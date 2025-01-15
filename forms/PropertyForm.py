from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, IntegerField
from wtforms.validators import DataRequired, Optional, ValidationError

from sqlalchemy import delete
from flask import redirect, render_template
from app.database import db, row2dict
from app.core.models.Clasess import Class, Object, Property, Value, Method
from app.core.main.ObjectsStorage import objects_storage
from plugins.Objects.forms.utils import no_spaces_or_dots, no_reserved, getMethodsParents

# Определение класса формы
class PropertyForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), no_spaces_or_dots, no_reserved])
    description = StringField('Description')
    method_id = SelectField("Method")
    history = IntegerField("History", validators=[Optional()])
    type = SelectField("Type")
    submit = SubmitField('Submit')
    id = None
    class_id = None
    object_id = None

    def validate_name(self, name):
        """Проверка на повторяющиеся значения в базе данных"""
        if self.object_id:
            if Property.query.filter(Property.name == name.data, Property.object_id == self.object_id, Property.id != self.id).first():
                raise ValidationError('Name already registered. Please choose a different one.')
        if self.class_id:
            if Property.query.filter(Property.name == name.data, Property.class_id == self.class_id, Property.id != self.id).first():
                raise ValidationError('Name already registered. Please choose a different one.')

def routeProperty(request):
    id = request.args.get('property', None)
    class_id = request.args.get('class', None)
    object_id = request.args.get('object', None)
    op = request.args.get('op', '')

    if op == 'delete':
        if object_id:
            prop_o = Property.query.filter(Property.object_id == object_id, Property.id == id).one_or_none()
            name = prop_o.name
            prop_c = Property.query.filter(Property.class_id == class_id, Property.id == id).one_or_none()
            if not prop_c:
                sql = delete(Value).where(Value.object_id == object_id, Value.name == name)
                db.session.execute(sql)
            sql = delete(Property).where(Property.id == id)
            db.session.execute(sql)
            db.session.commit()
        else:
            # todo delete value
            sql = delete(Property).where(Property.id == id)
            db.session.execute(sql)
            db.session.commit()

        if object_id: 
            url = "?view=object&object=" + str(object_id) + "&tab=properties"
            objects_storage.reload_object(object_id)
        else:
            url = "?view=class&class=" + str(class_id) + "&tab=properties"
            objects_storage.reload_objects_by_class(class_id)
        return redirect(url)

    if id:
        item = Property.query.get_or_404(id)  # Получаем объект из базы данных или возвращаем 404, если не найден
        form = PropertyForm(obj=item)  # Передаем объект в форму для редактирования
        form.id = id
    else:
        form = PropertyForm()
        form.history.data = 0

    form.class_id = class_id
    form.object_id = object_id

    object_owner = None
    if object_id:
        object_owner = Object.get_by_id(object_id)
        class_owner = Class.get_by_id(object_owner.class_id)
    else:
        class_owner = Class.get_by_id(class_id)
    methods = []
    if class_owner:
        methods = getMethodsParents(class_owner.id, methods)
    if object_id:
        obj_method = Method.query.filter(Method.object_id == object_id).all()
        for method in obj_method:
            methods.append(row2dict(method))

    form.method_id.choices = [('','')] + [(method['id'], method['name']) for method in methods]
    form.type.choices = [('',''),('int','Integer'),('float','Float'),('str','String'),('datetime','Datetime'),('dict','Dictionary'),('list','List')]
    if form.validate_on_submit():
        if id:
            if op == "redefine":
                prop = Property()
                prop.class_id = class_id
                prop.object_id = object_id
                prop.name = item.name
                prop.description = item.description
                prop.method_id = int(form.method_id.data) if form.method_id.data else None
                prop.history = form.history.data
                prop.type = form.type.data
                db.session.add(prop)
                db.session.commit()
                id = prop.id
            else:
                old_name = item.name
                form.populate_obj(item)  # Обновляем значения объекта данными из формы
                item.method_id = int(form.method_id.data) if form.method_id.data else None
                if old_name != item.name and object_id:
                    db.session.query(Value).filter(Value.object_id == object_id, Value.name == old_name).update({'name': item.name})
                if old_name != item.name and class_id:
                    objs = db.session.query(Object).filter(Object.class_id == class_id).all()
                    for obj in objs:
                        db.session.query(Value).filter(Value.object_id == obj.id, Value.name == old_name).update({'name': item.name})
        else:
            new_item = Property(
                name=form.name.data,
                description=form.description.data,
                method_id=int(form.method_id.data) if form.method_id.data else None,
                history=form.history.data,
                type=form.type.data,
            )
            if class_id:
                new_item.class_id = class_id
            if object_id:
                new_item.object_id = object_id
            db.session.add(new_item)
        db.session.commit()  # Сохраняем изменения в базе данных

        if object_id: 
            url = "?view=object&object=" + str(object_id) + "&tab=properties"
            objects_storage.reload_object(object_id)
        else:
            url = "?view=class&class=" + str(class_id) + "&tab=properties"
            objects_storage.reload_objects_by_class(class_id)

        return redirect(url)  # Перенаправляем на другую страницу после успешного редактирования
    content = {
        'id': id,
        'form':form,
        'class': class_owner,
        'object': object_owner,
    } 
    return render_template('property.html', **content)