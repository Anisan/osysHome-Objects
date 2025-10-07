from flask_wtf import FlaskForm
from wtforms import SubmitField, BooleanField
from wtforms.validators import Optional

# Определение класса формы
class SettingsForm(FlaskForm):
    render = BooleanField('View template in list objects', validators=[Optional()])
    submit = SubmitField('Submit')
