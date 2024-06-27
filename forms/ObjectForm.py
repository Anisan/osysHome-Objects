from flask import redirect, render_template
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, TextAreaField
from wtforms.validators import DataRequired
from sqlalchemy import delete

from app.database import db, row2dict
from app.core.lib.common import getJob
from app.core.models.Clasess import Class, Object, Property, Method, Value
from app.core.main.ObjectsStorage import remove_object, reload_object, objects
from plugins.Objects.forms.utils import *


# Определение класса формы
class ObjectForm(FlaskForm):
    id = None
    name = StringField('Name', validators=[DataRequired(), no_spaces_or_dots])
    description = StringField('Description')
    class_id = SelectField("Class")
    template = TextAreaField("Template", render_kw={"rows": 15})
    submit = SubmitField('Submit')

    def validate_name(self, name):
        obj = Object.query.filter(Object.name==name.data).first()
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
        remove_object(name)
        return redirect("Objects")
    
    properties = []
    methods = []
    classes = Class.query.order_by(Class.name).all()
    dict_classes = {obj.id: obj.name for obj in classes}
    choices = [('','')] + [(_class.id, _class.name) for _class in classes]
    if id:
        item = Object.query.get_or_404(id)  # Получаем объект из базы данных или возвращаем 404, если не найден
        class_id = item.class_id
        form = ObjectForm(obj=item)  # Передаем объект в форму для редактирования
        form.id = item.id
        parent_properties = []
        parent_properties = getPropertiesParents(item.class_id, parent_properties)
        object_properties = Property.query.filter(Property.object_id == item.id).order_by(Property.name).all()
        # исключить переопределенные
        parent_properties = [item for item in parent_properties if item['name'] not in [subitem.name for subitem in object_properties]]
        properties += parent_properties
        for c in object_properties:
            properties.append(row2dict(c))
        for property in properties:
            property['linked'] = []
            value = Value.query.filter(Value.object_id == id, Value.name == property['name']).one_or_none()
            if value:
                property['value'] = value.value
                property['source'] = value.source
                property['changed'] = value.changed
                if value.linked:
                    property['linked'] = value.linked.split(",")
        class_methods = []
        class_methods = getMethodsParents(item.class_id,class_methods)
        object_methods = Method.query.filter(Method.object_id == item.id).order_by(Method.name).all()
        for cls in class_methods:
            cls['redefined'] = False
            for o in object_methods:
                if o.name == cls["name"] and o.class_id == None:
                    cls['redefined'] = True
            methods.append(cls)

        for c in object_methods:
            m = row2dict(c)
            methods.append(m)
        for method in methods:
            if method['class_id']:
                method["class_name"] = dict_classes[method["class_id"]]
            job_name = item.name +"_"+ method['name']+"_periodic"
            job = getJob(job_name)
            if job:
                m['crontab'] = job['crontab']
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
            remove_object(old_name)
        reload_object(item.id)
        
        return redirect("Objects")  # Перенаправляем на другую страницу после успешного редактирования
    class_owner = None
    if class_id:
        class_owner = Class.get_by_id(class_id)
    obj = None
    if id:
        obj = objects[item.name]
    content = {
            'id': id,
            'form':form,
            'class': class_owner,
            'properties': properties,
            'methods': methods,
            'tab': tab,
            'obj': obj
            }
    return render_template('object.html', **content)
