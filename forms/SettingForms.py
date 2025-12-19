from flask_wtf import FlaskForm
from wtforms import SubmitField, BooleanField
from wtforms.validators import Optional


class SettingsForm(FlaskForm):
    """Настройки модуля Objects."""

    show_id = BooleanField('Show ID in lists', validators=[Optional()])
    render = BooleanField('View template in list objects', validators=[Optional()])
    submit = SubmitField('Submit')

