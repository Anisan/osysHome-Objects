from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, IntegerField, BooleanField
from wtforms.validators import DataRequired, Optional
from wtforms.widgets import PasswordInput

# Определение класса формы
class SettingsForm(FlaskForm):
    render = BooleanField('View template in list objects', validators=[Optional()])
    submit = SubmitField('Submit')