from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Optional

from flask import redirect, render_template
from sqlalchemy import or_, delete
from app.core.models.Clasess import Class, Property, Method, Object
from app.database import db
from .utils import *
from app.core.main.ObjectsStorage import remove_objects_by_class, reload_objects_by_class

# Определение класса формы
class ClassForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    description = StringField('Description')
    parent_id = SelectField("Parent", validators=[Optional()])
    template = TextAreaField("Template", render_kw={"rows": 15})
    submit = SubmitField('Submit')

def routeClass(request):
    id = request.args.get('class', None)
    tab = request.args.get('tab', '')
    op = request.args.get('op', '')
    if op == 'delete':
        #todo remove objects
        #todo remove classes
        sql = delete(Property).where(Property.class_id == id)
        db.session.execute(sql)
        sql = delete(Method).where(Method.class_id == id)
        db.session.execute(sql)
        sql = delete(Class).where(Class.id==id)
        db.session.execute(sql)
        db.session.commit()
        remove_objects_by_class(id)
        return redirect("Objects")
    if id:
        item = Class.query.get_or_404(id)  # Получаем объект из базы данных или возвращаем 404, если не найден
        form = ClassForm(obj=item)  # Передаем объект в форму для редактирования
        properties = Property.query.filter(Property.class_id == item.id, Property.object_id==None).order_by(Property.name).all()
        parent_properties = []
        if item.parent_id:
            parent_props = getPropertiesParents(item.parent_id, parent_properties)
            # исключить переопределенные
            parent_properties = [item for item in parent_props if item.name not in [subitem.name for subitem in properties]]

        methods = Method.query.filter(Method.class_id == item.id, Method.object_id==None).order_by(Method.name).all()
        parent_methods = []
        if item.parent_id:
            parent_methods = getMethodsParents(item.parent_id, parent_methods)
        objects = Object.query.filter(Object.class_id == id).order_by(Object.name).all()
    else:
        form = ClassForm()
        properties = []
        parent_properties = []
        methods = []
        parent_methods = []
        objects = []
    classes = Class.query.filter(Class.id != id).order_by(Class.name).all() # TODO exclude current class
    form.parent_id.choices = [('','')] +  [(_class.id, _class.name) for _class in classes]
    old_name = ""
    if id:
        old_name = item.name
    if form.validate_on_submit():
        if id:
            form.populate_obj(item)  # Обновляем значения объекта данными из формы
            item.parent_id = int(form.parent_id.data) if form.parent_id.data else None
        else:
            new_item = Class(
                name=form.name.data,
                description=form.description.data,
                parent_id = int(form.parent_id.data) if form.parent_id.data else None
            )
            db.session.add(new_item)
        db.session.commit()  # Сохраняем изменения в базе данных
        # update object to storage
        if id:
            if old_name != item.name:
                remove_objects_by_class(item.id)
            reload_objects_by_class(item.id)
        return redirect("Objects")  # Перенаправляем на другую страницу после успешного редактирования
    content = {
            'id': id,
            'form':form,
            'properties':properties,
            'parent_properties':parent_properties,
            'methods': methods,
            'parent_methods': parent_methods,
            'objects': objects,
            'tab': tab,
        }
    return render_template('class.html', **content)

