from app.database import row2dict
from app.core.models.Clasess import Class,Property, Method
from wtforms.validators import ValidationError

def getPropertiesParents(id, properties):
    props = Property.query.filter(Property.class_id == id, Property.object_id == None).order_by(Property.name).all()  # noqa
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
    meth = Method.query.filter(Method.class_id == id, Method.object_id == None).order_by(Method.name).all() # noqa
    cls = Class.get_by_id(id)
    for item in meth:
        item = row2dict(item)
        item["class_name"] = cls.name if cls else None
        methods.append(item)
    if cls and cls.parent_id:
        return getMethodsParents(cls.parent_id, methods)
    return methods

def no_spaces_or_dots(form, field):
    if ' ' in field.data or '.' in field.data:
        raise ValidationError('Field must not contain spaces or dots')
    
def no_reserved(form, field):
    if field.data == 'name' or field.data == 'description' or field.data == 'template':
        raise ValidationError('Field name "' + field.data + '" is reserved. Please choose a different one.')