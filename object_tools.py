import json
import re

from flask import jsonify, abort, request, Response
from sqlalchemy import delete

from app.database import db
from app.core.models.Clasess import Class, Object, Property, Method, Value, History
from app.core.main.ObjectsStorage import objects_storage
from app.core.lib.common import clearScheduledJob, getJobs
from plugins.Objects.forms.utils import checkPermission, getObjectId
from app.core.lib.object_tree import invalidate_objects_tree_cache
from app.core.lib.object_db import cleanup_orphan_records, delete_object_from_db

_NAME_RE = re.compile(r'^[^\s.]+$')


def routeObjectTools(req):
    object_id = getObjectId(req.args.get('object'))
    if not object_id:
        return jsonify({'success': False, 'message': 'Object not found'}), 400

    if not checkPermission(None, object_id):
        abort(403)

    obj = Object.query.get_or_404(object_id)
    op = req.args.get('op', '')

    if op == 'reload':
        objects_storage.reload_object(object_id)
        return jsonify({'success': True, 'message': 'Object reloaded in runtime'})

    if op == 'export_values':
        return _export_values(obj)

    if req.method != 'POST':
        return jsonify({'success': False, 'message': 'Method not allowed'}), 405

    data = req.get_json(silent=True) or {}

    if op == 'clear_history':
        return _clear_history(obj, data)
    if op == 'clear_links':
        return _clear_links(obj)
    if op == 'clear_schedules':
        return _clear_schedules(obj)
    if op == 'clone':
        return _clone_object(obj, data)
    if op == 'delete':
        return _delete_object(obj)
    if op == 'cleanup_orphans':
        stats = cleanup_orphan_records()
        db.session.commit()
        invalidate_objects_tree_cache()
        return jsonify({
            'success': True,
            'message': 'Orphan records cleaned up',
            **stats,
        })

    return jsonify({'success': False, 'message': 'Unknown operation'}), 400


def _delete_object(obj: Object):
    name = delete_object_from_db(obj.id)
    db.session.commit()
    invalidate_objects_tree_cache()
    if name:
        objects_storage.changeObject("delete", name, None, None, None)
        objects_storage.remove_object(name)
    return jsonify({
        'success': True,
        'message': 'Object deleted',
        'object_id': obj.id,
        'object_name': name,
    })


def _export_values(obj: Object):
    values = Value.query.filter(Value.object_id == obj.id).order_by(Value.name).all()
    payload = {
        'object': obj.name,
        'description': obj.description,
        'class': None,
        'values': [],
    }
    if obj.class_id:
        cls = Class.get_by_id(obj.class_id)
        if cls:
            payload['class'] = cls.name
    for val in values:
        payload['values'].append({
            'name': val.name,
            'value': val.value,
            'source': val.source,
            'changed': val.changed.isoformat() if val.changed else None,
            'linked': val.linked or '',
        })
    serialized = json.dumps(payload, ensure_ascii=False, indent=2)
    filename = f'values_{obj.name}.json'
    response = Response(serialized, content_type='application/json; charset=utf-8')
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def _clear_history(obj: Object, data: dict):
    property_name = (data.get('property') or '').strip()
    values = Value.query.filter(Value.object_id == obj.id).all()
    if not values:
        return jsonify({'success': True, 'message': 'No values for object', 'deleted_count': 0})

    if property_name:
        value_ids = [v.id for v in values if v.name == property_name]
        if not value_ids:
            return jsonify({'success': True, 'message': 'No history for property', 'deleted_count': 0, 'property': property_name})
    else:
        value_ids = [v.id for v in values]

    if not value_ids:
        return jsonify({'success': True, 'message': 'No history to clear', 'deleted_count': 0})

    result = db.session.execute(delete(History).where(History.value_id.in_(value_ids)))
    deleted_count = result.rowcount or 0
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'History cleared',
        'property': property_name or '*',
        'deleted_count': deleted_count,
    })


def _clear_links(obj: Object):
    values = Value.query.filter(Value.object_id == obj.id).all()
    cleared = 0
    for val in values:
        if val.linked:
            val.linked = ''
            cleared += 1
    db.session.commit()
    objects_storage.reload_object(obj.id)

    return jsonify({
        'success': True,
        'message': 'Links cleared',
        'cleared_count': cleared,
    })


def _clear_schedules(obj: Object):
    pattern = obj.name + r"\_%"  # noqa: W605
    jobs = getJobs(pattern)
    job_names = [job['name'] for job in jobs] if jobs else []
    if job_names:
        clearScheduledJob(pattern)
    return jsonify({
        'success': True,
        'message': 'Schedules cleared',
        'deleted_count': len(job_names),
        'jobs': job_names,
    })


def _clone_object(source: Object, data: dict):
    custom_name = (data.get('name') or '').strip()
    copy_description = bool(data.get('copy_description', True))
    description = source.description if copy_description else ''

    if custom_name:
        if not _NAME_RE.match(custom_name):
            return jsonify({'success': False, 'message': 'Invalid object name'}), 400
        if Object.query.filter(Object.name == custom_name).first():
            return jsonify({'success': False, 'message': 'Object name already exists'}), 400
        clone_name = custom_name
    else:
        base_name = source.name
        clone_name = f'{base_name}_clone'
        counter = 1
        while Object.query.filter(Object.name == clone_name).first():
            clone_name = f'{base_name}_clone_{counter}'
            counter += 1

    new_obj = Object(
        name=clone_name,
        description=description,
        class_id=source.class_id,
        template=source.template,
    )
    db.session.add(new_obj)
    db.session.flush()

    for prop in Property.query.filter(Property.object_id == source.id).all():
        db.session.add(Property(
            name=prop.name,
            description=prop.description,
            object_id=new_obj.id,
            type=prop.type,
            params=prop.params,
            method_id=prop.method_id,
            history=prop.history,
        ))

    for val in Value.query.filter(Value.object_id == source.id).all():
        db.session.add(Value(
            object_id=new_obj.id,
            name=val.name,
            value=val.value,
            source=val.source,
            changed=val.changed,
            linked=val.linked,
        ))

    for method in Method.query.filter(Method.object_id == source.id).all():
        db.session.add(Method(
            name=method.name,
            description=method.description,
            object_id=new_obj.id,
            code=method.code,
            call_parent=method.call_parent,
        ))

    db.session.commit()
    invalidate_objects_tree_cache()
    objects_storage.reload_object(new_obj.id)

    return jsonify({
        'success': True,
        'message': 'Object cloned',
        'object_id': new_obj.id,
        'object_name': clone_name,
    })
