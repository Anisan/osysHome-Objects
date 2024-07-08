from sqlalchemy import or_
from flask import render_template
from app.database import session_scope
from app.core.main.BasePlugin import BasePlugin
from app.core.models.Clasess import Class, Object, Property, Method, Object, Value
from plugins.Objects.forms.ClassForm import routeClass
from plugins.Objects.forms.ObjectForm import routeObject
from plugins.Objects.forms.PropertyForm import routeProperty
from plugins.Objects.forms.MethodForm import routeMethod

class Objects(BasePlugin):

    def __init__(self,app):
        super().__init__(app,__name__)
        self.title = "Objects Plugin"
        self.version = 1
        self.description = """Objects editor"""
        self.actions=["search", "widget"]

    def initialization(self):
        pass

    def admin(self, request):
        args = request.args
        data = request.data

        view = args.get('view', '')

        if view == "class":
            return routeClass(request)
        elif view == "object":
            return routeObject(request)
        elif view == "property":
            return routeProperty(request)
        elif view == "method":
            return routeMethod(request)
        
        classes = Class.query.filter(Class.parent_id == None).order_by(Class.name).all()
        cls_of_dicts = [
                {'id': c.id, 'name': c.name, 'description': c.description} 
                for c in classes
        ]
        for cls in cls_of_dicts:
                self.getClassInfo(cls)
        objects = Object.query.filter(Object.class_id == None).order_by(Object.name).all()
        objs_of_dicts = [
                {'id': obj.id, 'name': obj.name, 'description': obj.description} 
                for obj in objects
        ]
        content = {
                'classes' : cls_of_dicts,
                'objects' : objs_of_dicts,
                
        }
            
        return self.render('objects.html', content)
    
    def search(self, query: str) -> str:
        res = []
        classes = Class.query.filter(or_(Class.name.contains(query),Class.description.contains(query))).all()
        for cls in classes:
            res.append({"url":f'Objects?view=class&class={cls.id}', "title":f'{cls.name} ({cls.description})', "tags":[{"name":"Class","color":"danger"}]})
        objects = Object.query.filter(or_(Object.name.contains(query),Object.description.contains(query))).all()
        for obj in objects:
            res.append({"url":f'Objects?view=object&object={obj.id}', "title":f'{obj.name} ({obj.description})', "tags":[{"name":"Object","color":"warning"}]})
        props = Property.query.filter(or_(Property.name.contains(query),Property.description.contains(query))).all()
        for prop in props:
            if prop.class_id:
                cls = Class.get_by_id(prop.class_id)
                res.append({"url":f'Objects?view=property&class={prop.class_id}&property={prop.id}&op=edit', "title":f'{cls.name}.{prop.name} ({prop.description})', "tags":[{"name":"Property","color":"secondary"}]})    
            if prop.object_id:
                obj = Object.get_by_id(prop.object_id)
                res.append({"url":f'Objects?view=property&object={prop.object_id}&property={prop.id}&op=edit', "title":f'{obj.name}.{prop.name} ({prop.description})', "tags":[{"name":"Property","color":"primary"}]})    
        methods = Method.query.filter(or_(Method.name.contains(query),Method.description.contains(query),Method.code.contains(query))).all()
        for method in methods:
            if method.class_id:
                cls = Class.get_by_id(method.class_id)
                res.append({"url":f'Objects?view=method&class={method.class_id}&method={method.id}&op=edit', "title":f'{cls.name}.{method.name} ({method.description})', "tags":[{"name":"Method","color":"secondary"}]})    
            if method.object_id:
                obj = Object.get_by_id(method.object_id)
                res.append({"url":f'Objects?view=method&object={method.object_id}&method={method.id}&op=edit', "title":f'{obj.name}.{method.name} ({method.description})', "tags":[{"name":"Method","color":"primary"}]})    
        return res
    
    def widget(self):
        content = {}
        with session_scope() as session:
            content['classes_cnt'] = session.query(Class).count()
            content['objects_cnt'] = session.query(Object).count()
            content['values_cnt'] = session.query(Value).count()
        return render_template("widget_objects.html",**content)

    def getClassInfo(self, cls):

        childrens = Class.query.filter(Class.parent_id == cls["id"]).order_by(Class.name)

        list_of_dicts = [
                {'id': c.id, 'name': c.name, 'description': c.description} 
                for c in childrens
        ]
        cls["children"] = list_of_dicts
        for child in list_of_dicts:
            self.getClassInfo(child)
        
        objects = Object.query.filter(Object.class_id == cls["id"]).order_by(Object.name).all()
        cls["objects"] = objects

