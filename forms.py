from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional


class RegistrationForm(FlaskForm):
    username = StringField(
        "Имя пользователя",
        validators=[
            DataRequired(message="Введите имя пользователя"),
            Length(min=3, max=80, message="Имя должно быть от 3 до 80 символов"),
        ],
    )

    email = StringField(
        "Email",
        validators=[
            DataRequired(message="Введите email"),
            Email(message="Введите корректный email"),
            Length(max=120, message="Email слишком длинный"),
        ],
    )

    password = PasswordField(
        "Пароль",
        validators=[
            DataRequired(message="Введите пароль"),
            Length(min=8, message="Пароль должен быть минимум 8 символов"),
        ],
    )

    confirm = PasswordField(
        "Подтверждение пароля",
        validators=[
            DataRequired(message="Подтвердите пароль"),
            EqualTo("password", message="Пароли не совпадают"),
        ],
    )


class LoginForm(FlaskForm):
    username = StringField(
        "Имя пользователя",
        validators=[
            DataRequired(message="Введите имя пользователя"),
            Length(min=3, max=80, message="Имя должно быть от 3 до 80 символов"),
        ],
    )

    password = PasswordField(
        "Пароль",
        validators=[
            DataRequired(message="Введите пароль"),
        ],
    )


class SettingsForm(FlaskForm):
    username = StringField(
        "Имя пользователя",
        validators=[
            DataRequired(message="Введите имя пользователя"),
            Length(min=3, max=80, message="Имя должно быть от 3 до 80 символов"),
        ],
    )

    email = StringField(
        "Email",
        validators=[
            DataRequired(message="Введите email"),
            Email(message="Введите корректный email"),
            Length(max=120, message="Email слишком длинный"),
        ],
    )

    password = PasswordField(
        "Новый пароль",
        validators=[
            Optional(),
            Length(min=8, message="Новый пароль должен быть минимум 8 символов"),
        ],
    )

    confirm = PasswordField(
        "Подтверждение нового пароля",
        validators=[
            Optional(),
            EqualTo("password", message="Пароли не совпадают"),
        ],
    )