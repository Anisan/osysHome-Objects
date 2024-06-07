from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, TextAreaField
from wtforms.validators import DataRequired

from app.core.models.Clasess import Class, Object, Property, Method, Value
from app.core.lib.object import getProperty
from flask import redirect, render_template
from app.database import db, row2dict
from .utils import *
from sqlalchemy import delete
from app.core.main.ObjectsStorage import remove_object, reload_object
from app.core.lib.common import getJob


# Определение класса формы
class ObjectForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    description = StringField('Description')
    class_id = SelectField("Class")
    template = TextAreaField("Template", render_kw={"rows": 15})
    submit = SubmitField('Submit')

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
    choices = [(_class.id, _class.name) for _class in classes]
    if id:
        item = Object.query.get_or_404(id)  # Получаем объект из базы данных или возвращаем 404, если не найден
        class_id = item.class_id
        form = ObjectForm(obj=item)  # Передаем объект в форму для редактирования
        parent_properties = []
        parent_properties = getPropertiesParents(item.class_id, parent_properties)
        object_properties = Property.query.filter(Property.object_id == item.id).order_by(Property.name).all()
        # исключить переопределенные
        parent_properties = [item for item in parent_properties if item.name not in [subitem.name for subitem in object_properties]]
        for c in parent_properties:
            properties.append(row2dict(c))
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
        for c in class_methods:
            cls = row2dict(c)
            cls['redefined'] = False
            for o in object_methods:
                if o.name == c.name and o.class_id == None:
                    cls['redefined'] = True
            methods.append(cls)

        for c in object_methods:
            m = row2dict(c)
            methods.append(m)
        for method in methods:
            if method['class_id']:
                method["class_name"] = dict_classes[method["class_id"]]
            job = getJob(f'{item.name}_{c.name}_periodic')
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
        else:
            item = Object(
                name=form.name.data,
                description=form.description.data,
                class_id=form.class_id.data,
            )
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
    content = {
            'id': id,
            'form':form,
            'class': class_owner,
            'properties': properties,
            'methods': methods,
            'tab': tab,
            }
    return render_template('object.html', **content)
