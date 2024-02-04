from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, validators, SubmitField, SelectField, TextAreaField, FileField
from wtforms.validators import DataRequired, Length, Email, EqualTo


# Forma za prijavu korisnika
class LoginForm(FlaskForm):
    username = StringField('Korisničko ime', validators=[validators.DataRequired()])
    password = PasswordField('Lozinka', validators=[validators.DataRequired()])


# Forma za registraciju novog korisnika
class RegistrationForm(FlaskForm):
    first_name = StringField('Ime', validators=[DataRequired(), Length(min=2, max=20)])
    last_name = StringField('Prezime', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    username = StringField('Korisničko ime', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('Lozinka', validators=[DataRequired()])
    confirm_password = PasswordField('Potvrdi lozinku', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Registriraj se')


# Forma za odabir kviza - admin
class SelectQuizForm(FlaskForm):
    quiz = SelectField('Odaberi kviz', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Dalje')


# Forma za dodavanje pitanja - admin
class AddQuestionForm(FlaskForm):
    question_text = TextAreaField('Tekst pitanja', validators=[DataRequired()])
    option_a = StringField('Opcija A', validators=[DataRequired()])
    option_b = StringField('Opcija B', validators=[DataRequired()])
    option_c = StringField('Opcija C', validators=[DataRequired()])
    option_d = StringField('Opcija D', validators=[DataRequired()])
    correct_option = SelectField('Ispravna opcija', choices=[
        ('option_a', 'Opcija A'),
        ('option_b', 'Opcija B'),
        ('option_c', 'Opcija C'),
        ('option_d', 'Opcija D')],
                                 validators=[DataRequired()])
    image_upload = FileField('Dodaj sliku (opcionalno)')
    submit = SubmitField('Dodaj pitanje')
