import json
from flask_wtf import FlaskForm
from flask_login import current_user
from wtforms import StringField, SubmitField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Optional
from flask import redirect, render_template, abort
from sqlalchemy import delete
from app.core.models.Clasess import Class, Property, Method, Object
from app.database import db, row2dict
from plugins.Objects.forms.utils import getMethodsParents, getPropertiesParents, getTemplatesParents, get_class_hierarchy, get_objects_for_class_tree, no_spaces_or_dots, ValidationError, checkPermission, getClassId, normalize_call_parent
from app.core.main.ObjectsStorage import objects_storage
from app.core.lib.object import getObject
from app.core.lib.object_tree import invalidate_objects_tree_cache
from app.core.lib.object_db import delete_objects_by_class, cleanup_orphan_records

# Определение класса формы
class ClassForm(FlaskForm):
    id = None
    name = StringField('Name', validators=[DataRequired(), no_spaces_or_dots])
    description = StringField('Description')
    parent_id = SelectField("Parent", validators=[Optional()])
    template = TextAreaField("Template", render_kw={"rows": 15})
    submit = SubmitField('Submit')

    def validate_name(self, name):
        cls = Class.query.filter(Class.name == name.data).first()
        if self.id is None:
            if cls is not None:
                raise ValidationError('Class already taken. Please choose a different one.')
        else:
            if cls is not None and cls.id != self.id:
                raise ValidationError('Class already taken. Please choose a different one.')


def _load_class_properties_methods_and_objects(item, class_id, config):
    """
    Загружает properties, methods, objects и templates для класса.
    
    Args:
        item: Объект Class из БД
        class_id: ID класса
        config: Конфигурация приложения
    
    Returns:
        tuple: (properties, parent_properties, methods, parent_methods, objects, templates)
    """
    query = Property.query.filter(Property.class_id == item.id, Property.object_id.is_(None))
    if current_user.role not in ['admin','root']:
        query = query.filter(Property.name.notlike(r'\_%', escape='\\'))
    properties = query.order_by(Property.name).all()
    properties = [row2dict(prop) for prop in properties]
    parent_properties = []
    parent_property_names = set()
    if item.parent_id:
        parent_props = getPropertiesParents(item.parent_id, parent_properties)
        parent_property_names = {prop['name'] for prop in parent_props}
        # исключить переопределенные
        parent_properties = [prop for prop in parent_props if prop['name'] not in [subitem['name'] for subitem in properties]]
    
    dict_methods = {}
    query = Method.query.filter(Method.class_id == item.id, Method.object_id.is_(None))
    if current_user.role not in ['admin','root']:
        query = query.filter(Method.name.notlike(r'\_%', escape='\\'))
    methods = query.order_by(Method.name).all()
    methods = [row2dict(meth) for meth in methods]
    for method in methods:
        dict_methods[method['id']] = method['name']
    parent_methods = []
    parent_methods_by_name = {}
    if item.parent_id:
        parent_meths_all = getMethodsParents(item.parent_id, [])
        parent_methods_by_name = {meth['name']: meth for meth in parent_meths_all}
        # исключить переопределенные
        parent_methods = [meth for meth in parent_meths_all if meth['name'] not in [subitem['name'] for subitem in methods]]
    for method in parent_methods:
        dict_methods[method['id']] = method['name']

    for method in methods:
        parent_method = parent_methods_by_name.get(method['name'])
        method['redefined'] = parent_method is not None
        if parent_method:
            method['parent_method_id'] = parent_method['id']
            method['parent_class_id'] = parent_method['class_id']
            method['parent_class_name'] = parent_method.get('class_name')
        method['call_parent'] = normalize_call_parent(method.get('call_parent'))
    
    def _safe_parse_params(raw_params):
        """
        params могут храниться в БД как:
        - None / пустая строка
        - строка JSON (в т.ч. "null")
        - уже распарсенный dict (на некоторых ветках кода)
        """
        if not raw_params:
            return {}

        # Если сразу dict — используем как есть.
        if isinstance(raw_params, dict):
            return raw_params

        # Если строка — пытаемся распарсить как JSON.
        if isinstance(raw_params, str):
            try:
                parsed = json.loads(raw_params)
                return parsed if isinstance(parsed, dict) else {}
            except Exception:
                return {}

        # На неожиданные типы (list/int/etc.) не полагаемся.
        return {}

    for idx, method in enumerate(methods):
        method['_idx'] = idx
        params = _safe_parse_params(method.get('params'))
        method['params'] = params
        method['icon'] = params.get('icon', '')
        method['color'] = params.get('color', '')
        method['sort_order'] = params.get('sort_order')

    for idx, method in enumerate(parent_methods):
        method['_idx'] = idx
        params = _safe_parse_params(method.get('params'))
        method['params'] = params
        method['icon'] = params.get('icon', '')
        method['color'] = params.get('color', '')
        method['sort_order'] = params.get('sort_order')

    methods.sort(
        key=lambda m: (
            m['sort_order'] if m.get('sort_order') is not None else 10**9,
            m.get('_idx', 0),
        )
    )
    parent_methods.sort(
        key=lambda m: (
            m['sort_order'] if m.get('sort_order') is not None else 10**9,
            m.get('_idx', 0),
        )
    )

    # Обогащаем свойства и родительские свойства метаданными (icon, color, sort_order, validation params)
    for idx, prop in enumerate(properties):
        prop['_idx'] = idx  # исходный порядок
        prop['overrides_parent'] = prop['name'] in parent_property_names
        if prop['method_id']:
            if prop['method_id'] in dict_methods:
                prop['method'] = dict_methods[prop['method_id']]

        # Разбираем params (JSON) для доп. информации (icon, color, validation params)
        params = _safe_parse_params(prop.get('params'))

        prop['icon'] = params.get('icon', '')
        prop['color'] = params.get('color', '')
        prop['sort_order'] = params.get('sort_order')
        prop['params'] = params

    for idx, prop in enumerate(parent_properties):
        prop['_idx'] = idx  # исходный порядок внутри parent_properties
        if prop['method_id']:
            if prop['method_id'] in dict_methods:
                prop['method'] = dict_methods[prop['method_id']]

        # Для родительских свойств тоже пробуем разобрать icon/color/validation params
        params = _safe_parse_params(prop.get('params'))

        prop['icon'] = params.get('icon', '')
        prop['color'] = params.get('color', '')
        prop['sort_order'] = params.get('sort_order')
        prop['params'] = params

    # Сортируем: сначала по sort_order (если задан), затем по исходному порядку
    properties.sort(
        key=lambda p: (
            p['sort_order'] if p.get('sort_order') is not None else 10**9,
            p.get('_idx', 0),
        )
    )
    parent_properties.sort(
        key=lambda p: (
            p['sort_order'] if p.get('sort_order') is not None else 10**9,
            p.get('_idx', 0),
        )
    )

    query = Object.query.filter(Object.class_id == class_id)
    if current_user.role not in ['admin','root']:
        query = query.filter(Object.name.notlike(r'\_%', escape='\\'))
    objects = query.order_by(Object.name).all()
    objects = [
        {'id': obj.id, 'name': obj.name, 'description': obj.description, 'template': getObject(obj.name).render() if getObject(obj.name) and config.get("render", None) else ''}
        for obj in objects
    ]
    
    templates = {}
    if item.parent_id:
        templates = getTemplatesParents(item.parent_id, templates)
    
    return properties, parent_properties, methods, parent_methods, objects, templates


def _load_child_classes(class_id):
    query = Class.query.filter(Class.parent_id == class_id)
    if current_user.role not in ['admin', 'root']:
        query = query.filter(Class.name.notlike(r'\_%', escape='\\'))
    children = query.order_by(Class.name).all()
    child_classes = []
    for child in children:
        child_classes.append({
            'id': child.id,
            'name': child.name,
            'description': child.description,
            'children_count': Class.query.filter(Class.parent_id == child.id).count(),
            'objects_count': Object.query.filter(Object.class_id == child.id).count(),
        })
    return child_classes


def routeClass(request, config):
    id = request.args.get('class', None)
    id = getClassId(id)
    parent_param = request.args.get('parent', None)
    tab = request.args.get('tab', '')
    op = request.args.get('op', '')
    item = None

    if not checkPermission(id):
        abort(403)  # Возвращаем ошибку "Forbidden" если доступ запрещен

    if op == 'delete':
        delete_objects_by_class(id)
        sql = delete(Property).where(Property.class_id == id)
        db.session.execute(sql)
        sql = delete(Method).where(Method.class_id == id)
        db.session.execute(sql)
        sql = delete(Class).where(Class.id == id)
        db.session.execute(sql)
        db.session.commit()
        cleanup_orphan_records()
        db.session.commit()
        invalidate_objects_tree_cache()
        objects_storage.remove_objects_by_class(id)
        return redirect("Objects")
    if id:
        item = Class.query.get_or_404(id)  # Получаем объект из базы данных или возвращаем 404, если не найден
        form = ClassForm(obj=item)  # Передаем объект в форму для редактирования
        form.id = item.id
        properties, parent_properties, methods, parent_methods, objects, templates = _load_class_properties_methods_and_objects(item, id, config)

    else:
        form = ClassForm()
        properties = []
        parent_properties = []
        methods = []
        parent_methods = []
        objects = []
        templates = {}

    query = Class.query.filter(Class.id != id)  # TODO exclude current class
    if current_user.role not in ['admin','root']:
        query = query.filter(Class.name.notlike(r'\_%', escape='\\'))
    classes = query.order_by(Class.name).all()

    # TODO exclude current class
    form.parent_id.choices = [('','')] + [(_class.id, _class.name) for _class in classes]
    if not id and parent_param:
        parent_class_id = getClassId(parent_param)
        if parent_class_id and checkPermission(parent_class_id):
            form.parent_id.data = str(parent_class_id)
    old_name = ""
    if id:
        old_name = item.name
    saved = False
    if form.validate_on_submit():
        if id:
            form.populate_obj(item)  # Обновляем значения объекта данными из формы
            item.parent_id = int(form.parent_id.data) if form.parent_id.data else None
        else:
            item = Class(
                name=form.name.data,
                description=form.description.data,
                parent_id=int(form.parent_id.data) if form.parent_id.data else None
            )
            db.session.add(item)
        db.session.commit()  # Сохраняем изменения в базе данных
        invalidate_objects_tree_cache()
        # update object to storage
        saved = True
        # Обновляем id для нового класса, чтобы вкладки отображались
        if not id:
            id = item.id
            # Перезагружаем item из БД после создания
            item = Class.query.get_or_404(id)
            # Перезагружаем properties, methods, objects и templates для нового класса
            properties, parent_properties, methods, parent_methods, objects, templates = _load_class_properties_methods_and_objects(item, id, config)
            # Обновляем форму с данными созданного класса
            form = ClassForm(obj=item)
            form.id = item.id
            # Обновляем choices для parent_id
            query = Class.query.filter(Class.id != id)
            if current_user.role not in ['admin','root']:
                query = query.filter(Class.name.notlike(r'\_%', escape='\\'))
            classes = query.order_by(Class.name).all()
            form.parent_id.choices = [('','')] + [(_class.id, _class.name) for _class in classes]
        else:
            if old_name != item.name:
                objects_storage.remove_objects_by_class(item.id)
            objects_storage.reload_objects_by_class(item.id)
            # Перезагружаем данные после редактирования существующего класса
            properties, parent_properties, methods, parent_methods, objects, templates = _load_class_properties_methods_and_objects(item, id, config)
    tools_objects = []
    children_count = 0
    child_classes = []
    if id:
        tools_objects = [
            {'id': obj.id, 'name': obj.name, 'description': obj.description}
            for obj in get_objects_for_class_tree(id)
        ]
        child_classes = _load_child_classes(id)
        children_count = len(child_classes)

    content = {
        'id': id,
        'form':form,
        'properties':properties,
        'parent_properties':parent_properties,
        'methods': methods,
        'parent_methods': parent_methods,
        'objects': objects,
        'tools_objects': tools_objects,
        'children_count': children_count,
        'child_classes': child_classes,
        'templates': templates,
        'tab': tab,
        'show_id': config.get("show_id", False),
        'class_hierarchy': get_class_hierarchy(id) if id else [],
    }
    return render_template('class.html', **content)
