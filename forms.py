from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, EmailField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Regexp

class RegistrationForm(FlaskForm):
    """Форма регистрации нового пользователя"""
    username = StringField('Username', validators=[
        DataRequired(message='Имя пользователя обязательно'),
        Length(min=3, max=80, message='Имя пользователя должно быть от 3 до 80 символов')
    ])
    email = EmailField('Email', validators=[
        DataRequired(message='Email обязателен'),
        Email(message='Некорректный email адрес')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Пароль обязателен'),
        Length(min=8, message='Пароль должен быть не менее 8 символов'),
        Regexp(r'^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$',
               message='Пароль должен содержать хотя бы одну букву и одну цифру')
    ])
    confirm = PasswordField('Confirm Password', validators=[
        DataRequired(message='Подтверждение пароля обязательно'),
        EqualTo('password', message='Пароли не совпадают')
    ])

class LoginForm(FlaskForm):
    """Форма входа в систему"""
    username = StringField('Username', validators=[DataRequired(message='Имя пользователя обязательно')])
    password = PasswordField('Password', validators=[DataRequired(message='Пароль обязателен')])

class SettingsForm(FlaskForm):
    """Форма настроек профиля"""
    username = StringField('Username', validators=[
        DataRequired(message='Имя пользователя обязательно'),
        Length(min=3, max=80, message='Имя пользователя должно быть от 3 до 80 символов')
    ])
    email = EmailField('Email', validators=[
        DataRequired(message='Email обязателен'),
        Email(message='Некорректный email адрес')
    ])
    password = PasswordField('New Password', validators=[
        Length(min=8, message='Пароль должен быть не менее 8 символов'),
        Regexp(r'^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$',
               message='Пароль должен содержать хотя бы одну букву и одну цифру')
    ])
    confirm = PasswordField('Confirm Password', validators=[
        EqualTo('password', message='Пароли не совпадают')
    ])