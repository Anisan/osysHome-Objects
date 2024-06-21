from flask import redirect, render_template
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, RadioField, BooleanField
from wtforms.validators import DataRequired

from app.core.models.Clasess import Class, Object, Method
from app.core.lib.common import getJob, addCronJob, clearScheduledJob
from app.database import db
from sqlalchemy import delete
from app.core.main.ObjectsStorage import reload_object,reload_objects_by_class


# Определение класса формы
class MethodForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    description = StringField('Description')
    code = TextAreaField("Code", render_kw={"rows": 15})
    call_parent = RadioField("Call parent", choices=[('-1','Before'),('0','No'),('1','After')])
    periodic = BooleanField('Run periodic')
    crontab = StringField('Crontab')
    submit = SubmitField('Submit')

def routeMethod(request):
    id = request.args.get('method', None)
    class_id = request.args.get('class', None)
    object_id = request.args.get('object', None)
    op = request.args.get('op', '')
    saved = False

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
            url = "?view=object&object="+str(object_id)+"&tab=methods"
            reload_object(object_id)
        else:
            url = "?view=class&class="+str(class_id)+"&tab=methods"
            reload_objects_by_class(class_id)
        return redirect(url)
    if id:
        item = Method.query.get_or_404(id)  # Получаем объект из базы данных или возвращаем 404, если не найден
        form = MethodForm(obj=item)  # Передаем объект в форму для редактирования
        if object_owner and request.method == 'GET':
            job = getJob(f'{object_owner.name}_{item.name}_periodic')
            if job:
                form.periodic.data = True
                form.crontab.data = job['crontab']
    else:
        form = MethodForm()
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
                form.populate_obj(item)  # Обновляем значения объекта данными из формы
        else:
            item = Method(
                name=form.name.data,
                description=form.description.data,
            )
            if class_id:
                item.class_id = class_id
            if object_id:
                item.object_id = object_id
            db.session.add(item)

        if object_owner:
            # cron job
            clearScheduledJob(f'{object_owner.name}_{item.name}_periodic')
            if form.periodic.data == True and form.crontab.data != '':
                addCronJob(f'{object_owner.name}_{item.name}_periodic',f'callMethod("{object_owner.name}.{item.name}")',form.crontab.data)
        db.session.commit()  # Сохраняем изменения в базе данных
        
        if object_id: 
            url = "?view=object&object="+str(object_id)+"&tab=methods"
            reload_object(object_id)
        else:
            url = "?view=class&class="+str(class_id)+"&tab=methods"
            reload_objects_by_class(class_id)
        
        
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