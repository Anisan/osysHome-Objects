import json
from dateutil import parser
from flask import redirect, render_template, abort
from flask_wtf import FlaskForm
from flask_login import current_user
from wtforms import StringField, SubmitField, SelectField, TextAreaField, ValidationError
from wtforms.validators import DataRequired
from sqlalchemy import delete

from app.database import db, row2dict, convert_utc_to_local
from app.core.lib.common import getJobs
from app.core.utils import CustomJSONEncoder
from app.core.models.Clasess import Class, Object, Property, Method, Value
from app.core.main.ObjectsStorage import objects_storage
from plugins.Objects.forms.utils import no_spaces_or_dots, getPropertiesParents, getMethodsParents, checkPermission, getClassId, getObjectId


# Определение класса формы
class ObjectForm(FlaskForm):
    id = None
    name = StringField('Name', validators=[DataRequired(), no_spaces_or_dots])
    description = StringField('Description')
    class_id = SelectField("Class")
    template = TextAreaField("Template", render_kw={"rows": 15})
    submit = SubmitField('Submit')

    def validate_name(self, name):
        obj = Object.query.filter(Object.name == name.data).first()
        if self.id is None:
            if obj is not None:
                raise ValidationError('Object already taken. Please choose a different one.')
        else:
            if obj is not None and obj.id != self.id:
                raise ValidationError('Object already taken. Please choose a different one.')

def _load_object_properties_and_methods(item, object_id, dict_classes):
    """
    Загружает properties и methods для объекта.
    
    Args:
        item: Объект Object из БД
        object_id: ID объекта
        dict_classes: Словарь {class_id: class_name} для получения имен классов
    
    Returns:
        tuple: (properties, methods) - списки свойств и методов
    """
    properties = []
    methods = []
    
    # Загрузка properties
    parent_properties = []
    parent_properties = getPropertiesParents(item.class_id, parent_properties)
    query = Property.query.filter(Property.object_id == item.id)
    if current_user.role not in ['admin','root']:
        query = query.filter(Property.name.notlike(r'\_%', escape='\\'))
    object_properties = query.order_by(Property.name).all()
    # исключить переопределенные
    parent_properties = [prop for prop in parent_properties if prop['name'] not in [subitem.name for subitem in object_properties]]
    properties.extend(parent_properties)
    for c in object_properties:
        properties.append(row2dict(c))
    
    for property in properties:
        property['linked'] = []
        value = Value.query.filter(Value.object_id == object_id, Value.name == property['name']).one_or_none()
        if value:
            # Если в БД явно лежит None, не превращаем его в строку "None",
            # чтобы UI мог подставить default_value из params.
            if value.value is None:
                property['value'] = None
            elif property['type'] == 'datetime':
                try:
                    dt = parser.parse(value.value)
                    property['value'] = str(convert_utc_to_local(dt))
                except (ValueError, TypeError, AttributeError):
                    property['value'] = str(value.value)
            else:
                property['value'] = str(value.value)

            property['source'] = value.source if value.source else ''
            property['changed'] = convert_utc_to_local(value.changed) if value.changed else ''
            if value.linked:
                property['linked'] = value.linked.split(",")
        job_name = item.name + "\_" + property['name'] + "\_%"   # noqa
        jobs = getJobs(job_name)
        if jobs:
            property['jobs'] = jobs
    
    # Загрузка methods
    class_methods = []
    class_methods = getMethodsParents(item.class_id, class_methods)
    query = Method.query.filter(Method.object_id == item.id)
    if current_user.role not in ['admin','root']:
        query = query.filter(Method.name.notlike(r'\_%', escape='\\'))
    object_methods = query.order_by(Method.name).all()
    
    for cls in class_methods:
        cls['redefined'] = False
        for o in object_methods:
            if o.name == cls["name"] and o.class_id is None:
                cls['redefined'] = True
        methods.append(cls)

    for c in object_methods:
        m = row2dict(c)
        m['redefined'] = False
        methods.append(m)
    
    om = objects_storage.getObjectByName(item.name)
    for method in methods:
        if method['class_id']:
            method["class_name"] = dict_classes[method["class_id"]]
        job_name = item.name + "\_" + method['name'] + "\_%" # noqa
        jobs = getJobs(job_name)
        if jobs:
            method['jobs'] = jobs
        if method['name'] in om.methods and not method['redefined']:
            mm = om.methods[method['name']]
            method['source'] = mm.source if mm.source else ''
            method['executed'] = convert_utc_to_local(mm.executed) if mm.executed else ''
            method['exec_params'] = json.dumps(mm.exec_params, cls=CustomJSONEncoder) if mm.exec_params else ''
            method['exec_result'] = mm.exec_result if mm.exec_result else ''
            method['exec_time'] = mm.exec_time

    # Обогащаем свойства метаданными и считаем порядок сортировки
    for idx, property in enumerate(properties):
        property['_idx'] = idx  # исходный порядок
        # Проставляем имя метода, если он есть
        if property.get('method_id'):
            for method in methods:
                if method['id'] == property['method_id']:
                    property['method'] = method['name']
                    break

        # Разбираем params (JSON) для доп. информации
        params = {}
        raw_params = property.get('params')
        if raw_params:
            try:
                params = json.loads(raw_params)
            except Exception:
                params = {}

        property['params'] = params

        # read_only – используем в шаблоне, чтобы отключать редактирование
        property['read_only'] = bool(params.get('read_only', False))

        # icon и color – для визуального отображения в таблице
        property['icon'] = params.get('icon', '')
        property['color'] = params.get('color', '')

        # sort_order – используем для сортировки свойств в списке (меньше = выше)
        property['sort_order'] = params.get('sort_order')

        # default_value – если значение отсутствует в БД или равно None,
        # показываем значение по умолчанию вместо "None"
        has_explicit_value = 'value' in property and property['value'] is not None
        if not has_explicit_value and 'default_value' in params:
            property['value'] = params['default_value']

    # Сортируем свойства: сначала по sort_order (если задан), затем по исходному порядку
    properties.sort(
        key=lambda p: (
            p['sort_order'] if p.get('sort_order') is not None else 10**9,
            p.get('_idx', 0),
        )
    )
    
    return properties, methods

def routeObject(request, config):
    id = request.args.get('object', None)
    id = getObjectId(id)
    class_id = request.args.get('class', None)
    class_id = getClassId(class_id)
    tab = request.args.get('tab', '')
    op = request.args.get('op', '')

    if not checkPermission(None, id):
        abort(403)  # Возвращаем ошибку "Forbidden" если доступ запрещен

    if tab == 'permissions':
        item = Object.query.get_or_404(id)
        content = {
            'id': id,
            'type':'object',
            'name': item.name,
            'class_id': class_id,
            'tab': tab,
        }
        return render_template('objects_permissions.html', **content)

    if op == 'delete':
        # TODO delete linked
        sql = delete(Value).where(Value.object_id == id)
        db.session.execute(sql)
        sql = delete(Property).where(Property.object_id == id)
        db.session.execute(sql)
        sql = delete(Method).where(Method.object_id == id)
        db.session.execute(sql)
        cls = Object.get_by_id(id)
        name = cls.name
        sql = delete(Object).where(Object.id == id)
        db.session.execute(sql)
        db.session.commit()
        objects_storage.changeObject("delete",name, None, None, None)
        objects_storage.remove_object(name)
        return redirect("Objects")
    saved = False
    properties = []
    methods = []
    query = Class.query
    if current_user.role not in ['admin','root']:
        query = query.filter(Class.name.notlike(r'\_%', escape='\\'))
    classes = query.order_by(Class.name).all()

    dict_classes = {obj.id: obj.name for obj in classes}
    choices = [('','')] + [(_class.id, _class.name) for _class in classes]
    if id:
        item = Object.query.get_or_404(id)  # Получаем объект из базы данных или возвращаем 404, если не найден
        class_id = item.class_id
        form = ObjectForm(obj=item)  # Передаем объект в форму для редактирования
        form.id = item.id
        properties, methods = _load_object_properties_and_methods(item, id, dict_classes)

    else:
        form = ObjectForm()
        if class_id:
            form.class_id.data = class_id
    form.class_id.choices = choices
    old_name = ""
    if id:
        old_name = item.name
    if form.validate_on_submit():
        if id:
            form.populate_obj(item)  # Обновляем значения объекта данными из формы
            item.class_id = int(form.class_id.data) if form.class_id.data else None
        else:
            item = Object(
                name=form.name.data,
                description=form.description.data,
            )
            item.class_id = int(form.class_id.data) if form.class_id.data else None
            db.session.add(item)
        db.session.commit()  # Сохраняем изменения в базе данных
        # update object to storage
        if old_name != item.name:
            objects_storage.changeObject("rename", old_name, None, None, item.name)
            objects_storage.remove_object(old_name)
        objects_storage.reload_object(item.id)

        saved = True
        # Обновляем id для нового объекта, чтобы вкладки отображались
        if not id:
            id = item.id
            # Перезагружаем item из БД после создания
            item = Object.query.get_or_404(id)
            # Перезагружаем properties и methods для нового объекта
            properties, methods = _load_object_properties_and_methods(item, id, dict_classes)
            # Обновляем форму с данными созданного объекта
            form = ObjectForm(obj=item)
            form.id = item.id
            form.class_id.choices = choices
            class_id = item.class_id

        # return redirect("Objects")  # Перенаправляем на другую страницу после успешного редактирования
    class_owner = None
    if class_id:
        class_owner = Class.get_by_id(class_id)
    cls = None
    schedules = []
    template = ''
    if id:
        cls = objects_storage.getObjectByName(item.name)
        schedules = getJobs(item.name + "\_%")  # noqa
        template = cls.render()

    content = {
        'id': id,
        'form':form,
        'class': class_owner,
        'properties': properties,
        'methods': methods,
        'schedules': schedules,
        'template': template,
        'tab': tab,
        'obj': cls.to_dict() if cls else None,
        'saved': saved,
        'show_id': config.get("show_id", False),
    }
    return render_template('object.html', **content)
