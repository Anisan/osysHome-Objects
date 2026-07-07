from flask_login import current_user
from app.database import row2dict
from app.core.models.Clasess import Class, Object,Property, Method
from app.core.lib.object import getObject, getProperty
from wtforms.validators import ValidationError

def normalize_call_parent(value):
    if value is None or value == '':
        return -1
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0

def getPropertiesParents(id, properties):
    query = Property.query.filter(Property.class_id == id, Property.object_id.is_(None))
    if current_user.role not in ['admin','root']:
        query = query.filter(Property.name.notlike(r'\_%', escape='\\'))
    props = query.order_by(Property.name).all()

    cls = Class.get_by_id(id)
    for item in props:
        if item.name not in [subitem['name'] for subitem in properties]:
            item = row2dict(item)
            item["class_name"] = cls.name if cls else None
            properties.append(item)
    if cls and cls.parent_id:
        return getPropertiesParents(cls.parent_id, properties)
    return properties

def getMethodsParents(id, methods):
    query = Method.query.filter(Method.class_id == id, Method.object_id.is_(None))
    if current_user.role not in ['admin','root']:
        query = query.filter(Method.name.notlike(r'\_%', escape='\\'))
    meth = query.order_by(Method.name).all()

    cls = Class.get_by_id(id)
    for item in meth:
        if item.name not in [subitem['name'] for subitem in methods]:
            item = row2dict(item)
            item["class_name"] = cls.name if cls else None
            methods.append(item)
    if cls and cls.parent_id:
        return getMethodsParents(cls.parent_id, methods)
    return methods

def getTemplatesParents(id, templates):
    cls = Class.get_by_id(id)
    templates[cls.name] = cls.template
    if cls and cls.parent_id:
        return getTemplatesParents(cls.parent_id, templates)
    return templates

from app.core.lib.object_db import get_descendant_class_ids


def get_objects_for_class_tree(class_id):
    """Objects assigned to this class or any descendant class."""
    class_ids = get_descendant_class_ids(class_id)
    query = Object.query.filter(Object.class_id.in_(class_ids))
    if current_user.role not in ['admin', 'root']:
        query = query.filter(Object.name.notlike(r'\_%', escape='\\'))
    return query.order_by(Object.name).all()


def get_class_hierarchy(class_id):
    """Return class chain from root to class_id inclusive: [{'id': ..., 'name': ...}, ...]."""
    if not class_id:
        return []

    chain = []
    current_id = int(class_id)
    visited = set()

    while current_id and current_id not in visited:
        visited.add(current_id)
        cls = Class.get_by_id(current_id)
        if not cls:
            break
        chain.append({'id': cls.id, 'name': cls.name})
        current_id = cls.parent_id

    chain.reverse()
    return chain


def get_method_inheritance_chain(
    method_name,
    class_id,
    object_id=None,
    current_method_id=None,
    is_redefine=False,
    redefine_source_id=None,
):
    """Return method definitions from root class to current class/object."""
    if not method_name or not class_id:
        return []

    chain = []
    hierarchy = get_class_hierarchy(class_id)
    for cls in hierarchy:
        query = Method.query.filter(
            Method.name == method_name,
            Method.class_id == cls['id'],
            Method.object_id.is_(None),
        )
        if current_user.role not in ['admin', 'root']:
            query = query.filter(Method.name.notlike(r'\_%', escape='\\'))
        method = query.first()
        if method:
            chain.append({
                'id': method.id,
                'name': method.name,
                'code': method.code or '',
                'class_id': cls['id'],
                'class_name': cls['name'],
                'object_id': None,
                'owner': cls['name'],
                'owner_type': 'class',
                'call_parent': normalize_call_parent(method.call_parent),
                'is_current': current_method_id is not None and method.id == current_method_id,
                'is_source': is_redefine and redefine_source_id is not None and method.id == redefine_source_id,
                'is_new': False,
            })

    if object_id:
        query = Method.query.filter(
            Method.name == method_name,
            Method.object_id == object_id,
        )
        if current_user.role not in ['admin', 'root']:
            query = query.filter(Method.name.notlike(r'\_%', escape='\\'))
        method = query.first()
        if method:
            obj = Object.get_by_id(object_id)
            chain.append({
                'id': method.id,
                'name': method.name,
                'code': method.code or '',
                'class_id': None,
                'class_name': None,
                'object_id': object_id,
                'owner': obj.name if obj else '',
                'owner_type': 'object',
                'call_parent': normalize_call_parent(method.call_parent),
                'is_current': current_method_id is not None and method.id == current_method_id,
                'is_source': is_redefine and redefine_source_id is not None and method.id == redefine_source_id,
                'is_new': False,
            })

    if is_redefine:
        has_current_level = any(
            item['object_id'] == object_id and item['owner_type'] == 'object'
            for item in chain
        ) if object_id else any(
            item['class_id'] == class_id and item['owner_type'] == 'class'
            for item in chain
        )

        if not has_current_level:
            ctx_cls = Class.get_by_id(class_id)
            obj = Object.get_by_id(object_id) if object_id else None
            chain.append({
                'id': None,
                'name': method_name,
                'code': '',
                'class_id': class_id if not object_id else None,
                'class_name': ctx_cls.name if ctx_cls and not object_id else None,
                'object_id': object_id,
                'owner': obj.name if obj else (ctx_cls.name if ctx_cls else ''),
                'owner_type': 'object' if object_id else 'class',
                'call_parent': None,
                'is_current': True,
                'is_source': False,
                'is_new': True,
            })

    return chain

def no_spaces_or_dots(form, field):
    if ' ' in field.data or '.' in field.data:
        raise ValidationError('Field must not contain spaces or dots')

def no_reserved(form, field):
    if field.data == 'name' or field.data == 'description' or field.data == 'template':
        raise ValidationError('Field name "' + field.data + '" is reserved. Please choose a different one.')

def checkPermission(class_id: int = None, object_id: int = None, property_id: int = None, method_id: int = None):
    if not class_id and not object_id and not property_id and method_id:
        return True

    username = getattr(current_user, 'username', None)
    role = getattr(current_user, 'role', None)

    if role == "root":
        return True

    permissions = {}
    __permissions = {}

    if class_id:
        cls = Class.get_by_id(class_id)
        if cls:
            __permissions = getProperty("_permissions.class:" + cls.name)

    if object_id:
        obj = Object.get_by_id(object_id)
        if obj:
            item = getObject(obj.name)
            __permissions = object.__getattribute__(item, "__permissions")

    if __permissions and "self" in __permissions:
        permissions = __permissions["self"]
    if property_id:
        prop = Property.get_by_id(property_id)
        if prop and __permissions:
            if "properties" in __permissions:
                if prop.name in __permissions["properties"]:
                    permissions = __permissions["properties"][prop.name]
    if method_id:
        method = Method.get_by_id(method_id)
        if method and __permissions:
            if "methods" in __permissions:
                if method.name in __permissions["properties"]:
                    permissions = __permissions["properties"][method.name]

    if not permissions:
        return True

    if "edit" not in permissions:
        return True

    permissions = permissions["edit"]

    denied_users = permissions.get("denied_users",None)
    if denied_users and username in denied_users:
        return False
    access_users = permissions.get("access_users",None)
    if access_users and username in access_users:
        return True
    denied_roles = permissions.get("denied_roles",None)
    if denied_roles and role in denied_roles:
        return False
    access_roles = permissions.get("access_roles",None)
    if access_roles and role in access_roles:
        return True

    return False

def getClassId(id_or_name) -> str:
    if isinstance(id_or_name, str):
        if id_or_name.isdigit():
            return id_or_name
        cls = Class.query.where(Class.name == id_or_name).one_or_none()
        if cls:
            return str(cls.id)
    return id_or_name

def getObjectId(id_or_name) -> str:
    if isinstance(id_or_name, str):
        if id_or_name.isdigit():
            return id_or_name
        obj = Object.query.where(Object.name == id_or_name).one_or_none()
        if obj:
            return str(obj.id)
    return id_or_name

