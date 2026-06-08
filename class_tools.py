import re

from flask import jsonify, abort, request
from sqlalchemy import delete

from app.database import db
from app.core.models.Clasess import Class, Object, Value, History, Property, Method
from app.core.main.ObjectsStorage import objects_storage
from plugins.Objects.forms.utils import checkPermission, getClassId, get_objects_for_class_tree
from plugins.Objects.tree_cache import invalidate_objects_tree_cache

_NAME_RE = re.compile(r'^[^\s.]+$')
_MAX_BULK_CREATE = 100


def _delete_object(object_id: int) -> str:
    """Delete object from DB and runtime storage. Returns object name."""
    values = db.session.query(Value.id).filter(Value.object_id == object_id).all()
    value_ids = [v[0] for v in values]
    if value_ids:
        db.session.execute(delete(History).where(History.value_id.in_(value_ids)))
    db.session.execute(delete(Value).where(Value.object_id == object_id))
    db.session.execute(delete(Property).where(Property.object_id == object_id))
    db.session.execute(delete(Method).where(Method.object_id == object_id))
    obj = Object.get_by_id(object_id)
    if not obj:
        return ''
    name = obj.name
    db.session.execute(delete(Object).where(Object.id == object_id))
    objects_storage.changeObject("delete", name, None, None, None)
    objects_storage.remove_object(name)
    return name


def _class_tree_objects(class_id: int):
    return get_objects_for_class_tree(class_id)


def routeClassTools(req):
    class_id = getClassId(req.args.get('class'))
    if not class_id:
        return jsonify({'success': False, 'message': 'Class not found'}), 400

    if not checkPermission(class_id):
        abort(403)

    Class.query.get_or_404(class_id)
    op = req.args.get('op', '')

    if op == 'reload':
        objects_storage.reload_objects_by_class(class_id)
        reloaded_count = len(_class_tree_objects(class_id))
        return jsonify({
            'success': True,
            'message': 'Class reloaded in runtime',
            'reloaded_count': reloaded_count,
        })

    if req.method != 'POST':
        return jsonify({'success': False, 'message': 'Method not allowed'}), 405

    data = req.get_json(silent=True) or {}

    if op == 'bulk_create':
        return _bulk_create(class_id, data)
    if op == 'bulk_delete':
        return _bulk_delete(class_id)
    if op == 'clear_history':
        return _clear_history(class_id, data)
    if op == 'bulk_call_method':
        return _bulk_call_method(class_id, data)

    return jsonify({'success': False, 'message': 'Unknown operation'}), 400


def _bulk_create(class_id: int, data: dict):
    prefix = (data.get('prefix') or '').strip()
    separator = data.get('separator', '_')
    if separator is None:
        separator = '_'
    separator = str(separator)
    description = (data.get('description') or '').strip()

    try:
        start = int(data.get('start', 1))
        count = int(data.get('count', 1))
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'Invalid start or count'}), 400

    if not prefix or ' ' in prefix or '.' in prefix:
        return jsonify({'success': False, 'message': 'Invalid name prefix'}), 400
    if count < 1 or count > _MAX_BULK_CREATE:
        return jsonify({'success': False, 'message': f'Count must be between 1 and {_MAX_BULK_CREATE}'}), 400
    if start < 0:
        return jsonify({'success': False, 'message': 'Start index must be non-negative'}), 400

    created = []
    skipped = []
    new_ids = []

    for index in range(start, start + count):
        name = f'{prefix}{separator}{index}' if separator else f'{prefix}{index}'
        if not _NAME_RE.match(name):
            return jsonify({'success': False, 'message': f'Invalid object name: {name}'}), 400
        if Object.query.filter(Object.name == name).first():
            skipped.append(name)
            continue
        obj = Object(name=name, description=description, class_id=class_id)
        db.session.add(obj)
        db.session.flush()
        created.append(name)
        new_ids.append(obj.id)

    db.session.commit()
    invalidate_objects_tree_cache()
    for obj_id in new_ids:
        objects_storage.reload_object(obj_id)

    return jsonify({
        'success': True,
        'message': 'Objects created',
        'created': created,
        'skipped': skipped,
        'created_count': len(created),
        'skipped_count': len(skipped),
    })


def _bulk_delete(class_id: int):
    objs = _class_tree_objects(class_id)
    if not objs:
        return jsonify({'success': True, 'message': 'No objects to delete', 'deleted_count': 0, 'deleted': []})

    deleted = []
    object_ids = [obj.id for obj in objs]
    for object_id in object_ids:
        name = _delete_object(object_id)
        if name:
            deleted.append(name)

    db.session.commit()
    invalidate_objects_tree_cache()

    return jsonify({
        'success': True,
        'message': 'Objects deleted',
        'deleted': deleted,
        'deleted_count': len(deleted),
    })


def _clear_history(class_id: int, data: dict):
    property_name = (data.get('property') or '').strip()
    if not property_name:
        return jsonify({'success': False, 'message': 'Property not specified'}), 400

    objs = _class_tree_objects(class_id)
    if not objs:
        return jsonify({'success': True, 'message': 'No objects in class', 'deleted_count': 0})

    deleted_count = 0
    for obj in objs:
        values = Value.query.filter(Value.object_id == obj.id, Value.name == property_name).all()
        value_ids = [v.id for v in values]
        if not value_ids:
            continue
        result = db.session.execute(delete(History).where(History.value_id.in_(value_ids)))
        deleted_count += result.rowcount or 0

    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'History cleared',
        'property': property_name,
        'deleted_count': deleted_count,
    })


def _bulk_call_method(class_id: int, data: dict):
    method_name = (data.get('method') or '').strip()
    if not method_name:
        return jsonify({'success': False, 'message': 'Method not specified'}), 400

    objs = _class_tree_objects(class_id)
    results = []
    ok_count = 0
    error_count = 0

    for obj in objs:
        om = objects_storage.getObjectByName(obj.name)
        if not om:
            results.append({
                'object': obj.name,
                'success': False,
                'result': '',
                'error': 'Object not in runtime',
            })
            error_count += 1
            continue
        if method_name not in om.methods:
            results.append({
                'object': obj.name,
                'success': False,
                'result': '',
                'error': 'Method not found',
            })
            error_count += 1
            continue

        output = om.callMethod(method_name, {}, 'Objects:class_tools')
        if output is None:
            results.append({
                'object': obj.name,
                'success': False,
                'result': '',
                'error': 'Method not found',
            })
            error_count += 1
            continue

        result_text = str(output).rstrip('\n')
        results.append({
            'object': obj.name,
            'success': True,
            'result': result_text,
            'error': '',
        })
        ok_count += 1

    return jsonify({
        'success': True,
        'message': 'Methods executed',
        'method': method_name,
        'results': results,
        'ok_count': ok_count,
        'error_count': error_count,
        'total_count': len(results),
    })
