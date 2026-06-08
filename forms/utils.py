from flask_login import current_user
from app.database import row2dict
from app.core.models.Clasess import Class, Object,Property, Method
from app.core.lib.object import getObject, getProperty
from wtforms.validators import ValidationError

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

def get_descendant_class_ids(class_id):
    """Return class_id and all descendant (child) class IDs down the tree."""
    root_id = int(class_id)
    ids = [root_id]
    queue = [root_id]
    visited = {root_id}

    while queue:
        parent_id = queue.pop(0)
        children = Class.query.filter(Class.parent_id == parent_id).all()
        for child in children:
            if child.id in visited:
                continue
            visited.add(child.id)
            ids.append(child.id)
            queue.append(child.id)

    return ids


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

