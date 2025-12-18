from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, IntegerField, TextAreaField
from wtforms.validators import DataRequired, Optional, ValidationError

from sqlalchemy import delete
from flask import redirect, render_template, abort
from app.database import db, row2dict
from app.core.models.Clasess import Class, Object, Property, Value, Method
from app.core.main.ObjectsStorage import objects_storage
from plugins.Objects.forms.utils import no_spaces_or_dots, no_reserved, getMethodsParents, checkPermission, getObjectId, getClassId
import json
import ast

# Определение класса формы
class PropertyForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), no_spaces_or_dots, no_reserved])
    description = StringField('Description')
    method_id = SelectField("Method")
    history = IntegerField("History", validators=[Optional()])
    type = SelectField("Type")
    params = TextAreaField("Parameters (JSON)")
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

def normalize_params_json(params_str):
    """
    Normalize params string to valid JSON with string keys.
    Supports both JSON format and Python dict format.
    
    Examples:
        {0: "Value"} -> {"0": "Value"}
        {"0": "Value"} -> {"0": "Value"}
    """
    if not params_str or not params_str.strip():
        return None
    
    try:
        # Try to parse as JSON first
        params_dict = json.loads(params_str)
    except json.JSONDecodeError:
        try:
            # If JSON parsing fails, try Python literal eval (supports {0: "value"} format)
            params_dict = ast.literal_eval(params_str)
        except (ValueError, SyntaxError):
            return None
    
    # Convert all keys to strings
    if isinstance(params_dict, dict):
        normalized = {str(key): value for key, value in params_dict.items()}
        return json.dumps(normalized)
    
    return None

def routeProperty(request):
    class_id = request.args.get('class', None)
    class_id = getClassId(class_id)
    object_id = request.args.get('object', None)
    object_id = getObjectId(object_id)
    id = request.args.get('property', None)
    op = request.args.get('op', '')

    if not checkPermission(class_id, object_id, None, id):
        abort(403)  # Возвращаем ошибку "Forbidden" если доступ запрещен

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
            obj = Object.query.filter(Object.id == object_id).one_or_none()
            objects_storage.changeObject("delete", obj.name, name, None, None)
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
    form.type.choices = [('',''),('bool','Boolean'),('int','Integer'),('float','Float'),('str','String'),('datetime','Datetime'),('dict','Dictionary'),('list','List'),('enum','Enum')]
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
                # Handle params for enum type
                prop.params = normalize_params_json(form.params.data)
                db.session.add(prop)
                db.session.commit()
                id = prop.id
            else:
                old_name = item.name
                form.populate_obj(item)  # Обновляем значения объекта данными из формы
                item.method_id = int(form.method_id.data) if form.method_id.data else None
                # Handle params for enum type
                item.params = normalize_params_json(form.params.data)
                if old_name != item.name and object_id:
                    db.session.query(Value).filter(Value.object_id == object_id, Value.name == old_name).update({'name': item.name})
                if old_name != item.name and class_id:
                    objs = db.session.query(Object).filter(Object.class_id == class_id).all()
                    for obj in objs:
                        db.session.query(Value).filter(Value.object_id == obj.id, Value.name == old_name).update({'name': item.name})
                if object_owner and old_name != item.name:
                    objects_storage.changeObject("rename", object_owner.name, old_name, None, item.name)
        else:
            # Handle params for enum type
            params_data = normalize_params_json(form.params.data)
            
            new_item = Property(
                name=form.name.data,
                description=form.description.data,
                method_id=int(form.method_id.data) if form.method_id.data else None,
                history=form.history.data,
                type=form.type.data,
                params=params_data,
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
