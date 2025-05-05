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
from plugins.Objects.forms.utils import no_spaces_or_dots, getPropertiesParents, getMethodsParents, checkPermission


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

def routeObject(request):
    id = request.args.get('object', None)
    class_id = request.args.get('class', None)
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
        obj = Object.get_by_id(id)
        name = obj.name
        sql = delete(Object).where(Object.id == id)
        db.session.execute(sql)
        db.session.commit()
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
        parent_properties = []
        parent_properties = getPropertiesParents(item.class_id, parent_properties)
        query = Property.query.filter(Property.object_id == item.id)
        if current_user.role not in ['admin','root']:
            query = query.filter(Property.name.notlike(r'\_%', escape='\\'))
        object_properties = query.order_by(Property.name).all()
        # исключить переопределенные
        parent_properties = [item for item in parent_properties if item['name'] not in [subitem.name for subitem in object_properties]]
        properties += parent_properties
        for c in object_properties:
            properties.append(row2dict(c))
        for property in properties:
            property['linked'] = []
            value = Value.query.filter(Value.object_id == id, Value.name == property['name']).one_or_none()
            if value:
                if property['type'] == 'datetime':
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
            job_name = item.name + "\_" + property['name'] + "\_%"
            jobs = getJobs(job_name)
            if jobs:
                property['jobs'] = jobs
        class_methods = []
        class_methods = getMethodsParents(item.class_id,class_methods)
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
            job_name = item.name + "\_" + method['name'] + "\_%"
            jobs = getJobs(job_name)
            if jobs:
                method['jobs'] = jobs
            if method['name'] in om.methods and not method['redefined']:
                mm = om.methods[method['name']]
                method['source'] = mm.source if mm.source else ''
                method['executed'] = convert_utc_to_local(mm.executed) if mm.executed else ''
                method['exec_params'] = json.dumps(mm.exec_params, cls=CustomJSONEncoder) if mm.exec_params else ''
                method['exec_result'] = mm.exec_result if mm.exec_result else ''

        for property in properties:
            if property['method_id']:
                for method in methods:
                    if method['id'] == property['method_id']:
                        property['method'] = method['name']
                        break

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
            objects_storage.remove_object(old_name)
        objects_storage.reload_object(item.id)

        saved = True

        #return redirect("Objects")  # Перенаправляем на другую страницу после успешного редактирования
    class_owner = None
    if class_id:
        class_owner = Class.get_by_id(class_id)
    obj = None
    schedules = []
    template = ''
    if id:
        obj = objects_storage.getObjectByName(item.name)
        schedules = getJobs(item.name + "\_%")
        template = obj.render()

    content = {
        'id': id,
        'form':form,
        'class': class_owner,
        'properties': properties,
        'methods': methods,
        'schedules': schedules,
        'template': template,
        'tab': tab,
        'obj': obj,
        'saved': saved,
    }
    return render_template('object.html', **content)
