from flask import redirect, render_template, abort
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, RadioField, BooleanField
from wtforms.validators import DataRequired, ValidationError
from sqlalchemy import delete

from app.core.models.Clasess import Class, Object, Method
from app.core.lib.common import getJob, addCronJob, clearScheduledJob
from app.database import db
from app.core.main.ObjectsStorage import objects_storage
from plugins.Objects.forms.utils import no_spaces_or_dots, checkPermission, getClassId, getObjectId


# Определение класса формы
class MethodForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), no_spaces_or_dots])
    description = StringField('Description')
    code = TextAreaField("Code", render_kw={"rows": 15})
    call_parent = RadioField("Call parent", choices=[('-1','Before'),('0','No'),('1','After')])
    periodic = BooleanField('Run periodic')
    crontab = StringField('Crontab')
    submit = SubmitField('Submit')
    id = None
    class_id = None
    object_id = None

    def validate_name(self, name):
        """Проверка на повторяющиеся значения в базе данных"""
        if self.object_id:
            if Method.query.filter(Method.name == name.data, Method.object_id == self.object_id, Method.id != self.id).first():
                raise ValidationError('Name already registered. Please choose a different one.')
        if self.class_id:
            if Method.query.filter(Method.name == name.data, Method.class_id == self.class_id, Method.id != self.id).first():
                raise ValidationError('Name already registered. Please choose a different one.')

def routeMethod(request):
    id = request.args.get('method', None)
    if id is None:
        id = request.form.get('method',None)
        if id is not None:
            if id == 'None':
                id = None
            else:
                id = int(id)
    class_id = request.args.get('class', None)
    class_id = getClassId(class_id)
    object_id = request.args.get('object', None)
    object_id = getObjectId(object_id)
    op = request.args.get('op', '')
    saved = False

    if not checkPermission(class_id, object_id, id):
        abort(403)  # Возвращаем ошибку "Forbidden" если доступ запрещен

    object_owner = None
    if object_id:
        object_owner = Object.get_by_id(object_id)
        class_owner = Class.get_by_id(object_owner.class_id)
    else:
        class_owner = Class.get_by_id(class_id)

    if op == 'delete':
        sql = delete(Method).where(Method.id == id)
        db.session.execute(sql)
        db.session.commit()

        if object_id:
            url = "?view=object&object=" + str(object_id) + "&tab=methods"
            objects_storage.reload_object(object_id)
        else:
            url = "?view=class&class=" + str(class_id) + "&tab=methods"
            objects_storage.reload_objects_by_class(class_id)
        return redirect(url)

    if id:
        item = Method.query.get_or_404(id)  # Получаем объект из базы данных или возвращаем 404, если не найден
        form = MethodForm(obj=item)  # Передаем объект в форму для редактирования
        form.id = id
        if object_owner and request.method == 'GET':
            job = getJob(f'{object_owner.name}_{item.name}_periodic')
            if job:
                form.periodic.data = True
                form.crontab.data = job['crontab']
    else:
        form = MethodForm()
        form.call_parent.data = '0'

    form.class_id = class_id
    form.object_id = object_id

    if form.validate_on_submit():
        if id:
            if op == "redefine":
                method = Method()
                method.class_id = class_id
                method.object_id = object_id
                method.name = form.name.data
                method.description = form.description.data
                method.code = form.code.data
                method.call_parent = form.call_parent.data
                db.session.add(method)
                db.session.commit()
                id = method.id
            else:
                old_name = item.name
                form.populate_obj(item)  # Обновляем значения объекта данными из формы
                if object_owner and old_name != item.name:
                    objects_storage.changeObject("rename", object_owner.name, None, old_name, item.name)
        else:
            item = Method(
                name=form.name.data,
                description=form.description.data,
                code=form.code.data,
                call_parent=form.call_parent.data,
            )
            if class_id:
                item.class_id = class_id
            if object_id:
                item.object_id = object_id
            db.session.add(item)
            db.session.commit()
            id = item.id

        if object_owner:
            # cron job
            clearScheduledJob(f'{object_owner.name}_{item.name}_periodic')
            if form.periodic.data and form.crontab.data != '':
                addCronJob(f'{object_owner.name}_{item.name}_periodic',f'callMethod("{object_owner.name}.{item.name}")',form.crontab.data)
        db.session.commit()  # Сохраняем изменения в базе данных

        if object_id:
            url = "?view=object&object=" + str(object_id) + "&tab=methods"
            objects_storage.reload_object(object_id)
        else:
            url = "?view=class&class=" + str(class_id) + "&tab=methods"
            objects_storage.reload_objects_by_class(class_id)

        saved = True

    if op == "redefine":
        form.code.data = ""
    content = {
        'id': id,
        'form':form,
        'class': class_owner,
        'object': object_owner,
        'saved': saved,
    }
    return render_template('method.html', **content)
