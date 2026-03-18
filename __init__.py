from sqlalchemy import or_
from flask import render_template, jsonify
from flask_login import current_user
from app.database import session_scope
from app.core.main.BasePlugin import BasePlugin
from app.core.models.Clasess import Class, Object, Property, Method, Value
from plugins.Objects.forms.ClassForm import routeClass
from plugins.Objects.forms.ObjectForm import routeObject
from plugins.Objects.forms.PropertyForm import routeProperty
from plugins.Objects.forms.MethodForm import routeMethod
from plugins.Objects.forms.ScheduleForm import routeSchedule
from plugins.Objects.forms.SettingForms import SettingsForm
from app.core.lib.object import getObject
from plugins.Objects.tree_cache import (
    get_objects_tree_payload,
    attach_object_templates,
)

class Objects(BasePlugin):

    def __init__(self,app):
        super().__init__(app,__name__)
        self.title = "Objects"
        self.version = "1.0"
        self.description = """Objects editor"""
        self.actions = ["search", "widget"]
        self.category = "System"
        self.author = "Eraser"

    def initialization(self):
        pass

    def admin(self, request):
        args = request.args
        view = args.get('view', '')

        if view == "class":
            return routeClass(request, self.config)
        elif view == "object":
            return routeObject(request, self.config)
        elif view == "property":
            return routeProperty(request)
        elif view == "method":
            return routeMethod(request)
        elif view == "schedule":
            return routeSchedule(request)
        elif view == "permissions":
            content = {
                'id': None,
                'type':'object',
                'name': "*",
                'tab': None,
            }
            return render_template('objects_permissions.html', **content)
        elif view == "reload":
            from app.core.main.ObjectsStorage import objects_storage
            typeReload = args.get('type', None)
            id = args.get('id', None)
            if typeReload == "class" and id:
                objects_storage.remove_objects_by_class(id)
            if typeReload == "object" and id:
                objects_storage.remove_object(id)
            return "Ok"
        elif view == "tree_children":
            class_id = args.get('class', None)
            if not class_id:
                return jsonify({"html": ""})
            try:
                class_id = int(class_id)
            except (TypeError, ValueError):
                return jsonify({"html": "", "error": "invalid class id"}), 400

            include_hidden = current_user.role in ['admin', 'root']
            render_templates = bool(self.config.get("render", None))
            tree_payload = get_objects_tree_payload(include_hidden=include_hidden)
            parent_class = tree_payload["classes_by_id"].get(class_id)
            if parent_class is None:
                return jsonify({"html": "", "error": "class not found"}), 404

            html = render_template(
                'objects_tree_branch.html',
                classes=tree_payload["children_by_parent"].get(class_id, []),
                objects=attach_object_templates(
                    tree_payload["objects_by_class"].get(class_id, []),
                    render_templates=render_templates,
                ),
                show_id=self.config.get('show_id', False),
                parent_class=parent_class,
            )
            return jsonify({"html": html})

        settings = SettingsForm()
        if request.method == 'GET':
            settings.render.data = self.config.get('render', False)
            settings.show_id.data = self.config.get('show_id', False)
        else:
            if settings.validate_on_submit():
                self.config["render"] = settings.render.data
                self.config["show_id"] = settings.show_id.data
                self.saveConfig()

        render_templates = bool(self.config.get("render", None))
        show_id = self.config.get('show_id', False)
        include_hidden = current_user.role in ['admin', 'root']
        tree_payload = get_objects_tree_payload(include_hidden=include_hidden)
        total_objects_count = len(tree_payload['standalone_objects']) + sum(
            len(items) for items in tree_payload['objects_by_class'].values()
        )

        content = {
            'classes': tree_payload['root_classes'],
            'objects': attach_object_templates(
                tree_payload['standalone_objects'],
                render_templates=render_templates,
            ),
            'root_class_count': len(tree_payload['root_classes']),
            'standalone_object_count': len(tree_payload['standalone_objects']),
            'total_class_count': len(tree_payload['classes_by_id']),
            'total_object_count': total_objects_count,
            'form': settings,
            'show_id': show_id,
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

        values = Value.query.filter(Value.value.contains(query)).all()
        for val in values:
            obj = Object.get_by_id(val.object_id)
            res.append({"url":f'Objects?view=object&object={val.object_id}&tab=properties', "title":f'{obj.name}.{val.name} = {val.value}', "tags":[{"name":"Value","color":"success"}]})

        return res

    def widget(self):
        content = {}
        with session_scope() as session:
            content['classes_cnt'] = session.query(Class).count()
            content['objects_cnt'] = session.query(Object).count()
            content['values_cnt'] = session.query(Value).count()
        return render_template("widget_objects.html",**content)

    def getClassInfo(self, cls):
        """
        Legacy recursive tree builder kept for backward-compatibility.
        The main admin view now builds the tree in bulk (see admin()).
        """
        query = Class.query.filter(Class.parent_id == cls["id"])
        if current_user.role not in ['admin', 'root']:
            query = query.filter(Class.name.notlike(r'\_%', escape='\\'))
        childrens = query.order_by(Class.name).all()

        list_of_dicts = [
            {'id': c.id, 'name': c.name, 'description': c.description}
            for c in childrens
        ]
        cls["children"] = list_of_dicts
        for child in list_of_dicts:
            self.getClassInfo(child)

        query = Object.query.filter(Object.class_id == cls["id"])
        if current_user.role not in ['admin', 'root']:
            query = query.filter(Object.name.notlike(r'\_%', escape='\\'))
        objects = query.order_by(Object.name).all()

        render_templates = bool(self.config.get("render", None))
        objs_of_dicts = []
        for obj in objects:
            obj_runtime = getObject(obj.name) if render_templates else None
            objs_of_dicts.append({
                'id': obj.id,
                'name': obj.name,
                'description': obj.description,
                'template': obj_runtime.render() if obj_runtime else ''
            })
        cls["objects"] = objs_of_dicts
