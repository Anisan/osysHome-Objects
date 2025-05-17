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
