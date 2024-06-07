from sqlalchemy import or_
from app.core.models.Clasess import Class,Property, Method

def getPropertiesParents(id, properties):
    props = Property.query.filter(Property.class_id==id, or_(Property.object_id == None)).order_by(Property.name).all()
    props = [item for item in props if item.name not in [subitem.name for subitem in properties]]
    properties = properties + props
    cls = Class.get_by_id(id)
    if cls.parent_id:
        return getPropertiesParents(cls.parent_id, properties)
    return properties

def getMethodsParents(id, methods):
    meth = Method.query.filter(Method.class_id==id, or_(Method.object_id == None)).order_by(Method.name).all()
    methods = methods + meth
    cls = Class.get_by_id(id)
    if cls.parent_id:
        return getMethodsParents(cls.parent_id, methods)
    return methods