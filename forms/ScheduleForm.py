
from app.database import db, row2dict
from sqlalchemy import delete
from flask import redirect, render_template
from app.core.models.Clasess import Class, Object, Property, Value, Method
from app.core.models.Tasks import Task
from app.core.lib.common import getJob
import datetime
from app.core.lib.crontab import nextStartCronJob
from flask_wtf import  FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, DateTimeLocalField
from wtforms.validators import DataRequired, Optional


class TaskForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    code = TextAreaField('Code', validators=[DataRequired()])
    crontab = StringField('Crontab',validators=[Optional()])
    runtime = DateTimeLocalField('Runtime',validators=[Optional()])
    submit = SubmitField('Submit')

def addPrefix(name,num):
    search = f'{name}_{num}'
    job = getJob(search)
    if not job:
        return search
    return addPrefix(name, num + 1)

def routeSchedule(request):
    op = request.args.get('op', '')
    schedule_id = request.args.get('schedule', None)
    object_id = request.args.get('object', None)
    tab = request.args.get('tab', None)
    property_id = request.args.get('property', None)
    method_id = request.args.get('method', None)

    if op == 'delete':
        # Delete a route schedule
        if schedule_id:
            sql = delete(Task).where(Task.id == schedule_id)
            db.session.execute(sql)
            db.session.commit()
            url = f"?view=object&object={object_id}&tab={tab}"
            return redirect(url)
        
    obj = Object.query.get(object_id)
    if property_id:
        tab = "properties"
    if method_id:
        tab = "methods"

    form = TaskForm()

    if form.validate_on_submit():
        # Create a new route schedule
        if schedule_id:
            task = Task.query.get(schedule_id)
            task.name = form.name.data
            task.code = form.code.data
            task.crontab = form.crontab.data
            task.runtime = form.runtime.data
        else:
            task = Task(name=form.name.data, code=form.code.data, crontab=form.crontab.data)
            db.session.add(task)
        
        if form.crontab.data == "":
            task.crontab = None
            if not form.runtime.data:
                task.runtime = datetime.datetime.now()
                task.expire = datetime.datetime.now() + datetime.timedelta(1800)
            else:
                task.runtime = form.runtime.data
                task.expire = form.runtime.data + datetime.timedelta(1800)
        else:
            dt = nextStartCronJob(task.crontab)
            task.runtime = dt
            task.expire = dt + datetime.timedelta(1800)

        db.session.commit()
        url = f"?view=object&object={object_id}&tab={tab}"
        return redirect(url)
    
    if schedule_id:
        task = Task.query.get(schedule_id)
        form.name.data = task.name
        form.code.data = task.code
        form.crontab.data = task.crontab
        form.runtime.data = task.runtime
    else:
        name = ''
        code = ''
        if property_id:
            prop = Property.query.get(property_id)
            name = f'{obj.name}_{prop.name}_task' # todo get number
            code = f'setProperty("{obj.name}.{prop.name}", [value] , source="Scheduler")'
        if method_id:
            method = Method.query.get(method_id)
            name = f'{obj.name}_{method.name}_task' # todo get number
            code = f'callMethod("{obj.name}.{method.name}", source="Scheduler")'

        name = addPrefix(name,1)
       
        form.name.data = name
        form.code.data = code

    content = {
        'id': schedule_id,
        'object_id': object_id,
        'object_name': obj.name,
        'tab': tab,
        'form':form,
    } 
    return render_template('object_schedule.html', **content)
