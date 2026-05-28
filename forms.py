from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, Regexp, ValidationError


USERNAME_VALIDATORS = [
    DataRequired(message="Enter a username."),
    Length(min=3, max=40, message="Username must be 3 to 40 characters long."),
    Regexp(
        r"^[A-Za-zА-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһ0-9_.-]+$",
        message="Use letters, numbers, dots, hyphens or underscores.",
    ),
]

EMAIL_VALIDATORS = [
    DataRequired(message="Enter an email address."),
    Email(message="Enter a valid email address."),
    Length(max=120, message="Email is too long."),
]


class RegistrationForm(FlaskForm):
    username = StringField("Username", validators=USERNAME_VALIDATORS)
    email = StringField("Email", validators=EMAIL_VALIDATORS)
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(message="Enter a password."),
            Length(min=8, max=128, message="Password must be 8 to 128 characters long."),
        ],
    )
    confirm = PasswordField(
        "Confirm password",
        validators=[
            DataRequired(message="Confirm your password."),
            EqualTo("password", message="Passwords do not match."),
        ],
    )


class LoginForm(FlaskForm):
    username = StringField("Username", validators=USERNAME_VALIDATORS)
    password = PasswordField("Password", validators=[DataRequired(message="Enter a password.")])


class SettingsForm(FlaskForm):
    username = StringField("Username", validators=USERNAME_VALIDATORS)
    email = StringField("Email", validators=EMAIL_VALIDATORS)
    current_password = PasswordField("Current password", validators=[Optional()])
    password = PasswordField(
        "New password",
        validators=[
            Optional(),
            Length(min=8, max=128, message="New password must be 8 to 128 characters long."),
        ],
    )
    confirm = PasswordField(
        "Confirm new password",
        validators=[Optional(), EqualTo("password", message="Passwords do not match.")],
    )

    def validate_confirm(self, field):
        if self.password.data and not field.data:
            raise ValidationError("Confirm the new password.")


class DeleteAccountForm(FlaskForm):
    password = PasswordField("Password", validators=[DataRequired(message="Enter your password.")])
