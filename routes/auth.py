from hmac import compare_digest

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from extensions import bcrypt, db, limiter
from forms import DeleteAccountForm, LoginForm, RegistrationForm, SettingsForm
from models import User
from services.security import safe_redirect_target
from translations import DEFAULT_LANG, TRANSLATIONS

bp = Blueprint("auth", __name__)


def tr(key):
    from flask import session

    lang = session.get("lang", DEFAULT_LANG)
    return TRANSLATIONS.get(lang, {}).get(key, TRANSLATIONS[DEFAULT_LANG].get(key, key))


ERROR_KEYS = {
    "Enter a username.": "validation.username_required",
    "Username must be 3 to 40 characters long.": "validation.username_length",
    "Use letters, numbers, dots, hyphens or underscores.": "validation.username_charset",
    "Enter an email address.": "validation.email_required",
    "Enter a valid email address.": "validation.email_invalid",
    "Email is too long.": "validation.email_length",
    "Enter a password.": "validation.password_required",
    "Password must be 8 to 128 characters long.": "validation.password_length",
    "Confirm your password.": "validation.confirm_required",
    "Passwords do not match.": "validation.password_mismatch",
    "New password must be 8 to 128 characters long.": "validation.new_password_length",
    "Confirm the new password.": "validation.new_password_confirm",
    "Enter your password.": "validation.password_required",
}


def localize_form_errors(form):
    for field in form:
        field.errors = [tr(ERROR_KEYS.get(error, error)) for error in field.errors]


def valid_admin_setup_token(token):
    expected = current_app.config.get("ADMIN_SETUP_TOKEN", "")
    return bool(expected and token and compare_digest(str(expected), str(token)))


@bp.route("/setup-admin", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def setup_admin():
    token = request.values.get("token", "")
    if not valid_admin_setup_token(token):
        abort(404)

    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        email = form.email.data.strip().lower()
        password_hash = bcrypt.generate_password_hash(form.password.data).decode("utf-8")
        user = User.query.filter_by(email=email).first()

        if user:
            if User.query.filter(User.username == username, User.id != user.id).first():
                flash(tr("flash.username_taken"), "danger")
                return render_template("setup_admin.html", form=form, token=token)
            user.username = username
            user.password_hash = password_hash
            user.role = "admin"
            flash(tr("setup_admin.promoted"), "success")
        else:
            if User.query.filter_by(username=username).first():
                flash(tr("flash.username_taken"), "danger")
                return render_template("setup_admin.html", form=form, token=token)
            user = User(
                username=username,
                email=email,
                role="admin",
                password_hash=password_hash,
            )
            db.session.add(user)
            flash(tr("setup_admin.created"), "success")

        db.session.commit()
        login_user(user, remember=True)
        return redirect(url_for("main.admin_dashboard"))

    localize_form_errors(form)
    return render_template("setup_admin.html", form=form, token=token)


@bp.route("/register", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.workspace"))

    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        email = form.email.data.strip().lower()

        if User.query.filter_by(username=username).first():
            flash(tr("flash.username_taken"), "danger")
            return render_template("register.html", form=form)

        if User.query.filter_by(email=email).first():
            flash(tr("flash.email_taken"), "danger")
            return render_template("register.html", form=form)

        user = User(
            username=username,
            email=email,
            password_hash=bcrypt.generate_password_hash(form.password.data).decode("utf-8"),
        )
        db.session.add(user)
        db.session.commit()

        flash(tr("flash.account_created"), "success")
        return redirect(url_for("auth.login"))

    localize_form_errors(form)
    return render_template("register.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("15 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.workspace"))

    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        user = User.query.filter_by(username=username).first()

        if not user or not bcrypt.check_password_hash(user.password_hash, form.password.data):
            flash(tr("flash.invalid_login"), "danger")
            return render_template("login.html", form=form)

        login_user(user, remember=True)
        flash(tr("flash.welcome"), "success")

        next_page = safe_redirect_target(request.args.get("next"), url_for("main.workspace"))
        return redirect(next_page)

    localize_form_errors(form)
    return render_template("login.html", form=form)


@bp.route("/logout", methods=["GET", "POST"])
def logout():
    if current_user.is_authenticated:
        logout_user()
        flash(tr("flash.signed_out"), "info")
    return redirect(url_for("main.index"))


@bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    form = SettingsForm(obj=current_user)
    delete_form = DeleteAccountForm()

    if request.method == "GET":
        form.username.data = current_user.username
        form.email.data = current_user.email

    if form.validate_on_submit():
        username = form.username.data.strip()
        email = form.email.data.strip().lower()
        new_password = (form.password.data or "").strip()
        current_password = (form.current_password.data or "").strip()

        if User.query.filter(User.username == username, User.id != current_user.id).first():
            flash(tr("flash.username_taken"), "danger")
            return render_template("settings.html", form=form, delete_form=delete_form)

        if User.query.filter(User.email == email, User.id != current_user.id).first():
            flash(tr("flash.email_taken"), "danger")
            return render_template("settings.html", form=form, delete_form=delete_form)

        if new_password:
            if not current_password or not bcrypt.check_password_hash(
                current_user.password_hash,
                current_password,
            ):
                flash(tr("flash.current_password_required"), "danger")
                return render_template("settings.html", form=form, delete_form=delete_form)
            current_user.password_hash = bcrypt.generate_password_hash(new_password).decode("utf-8")

        current_user.username = username
        current_user.email = email
        db.session.commit()

        flash(tr("flash.settings_saved"), "success")
        return redirect(url_for("auth.settings"))

    localize_form_errors(form)
    return render_template("settings.html", form=form, delete_form=delete_form)


@bp.route("/delete-account", methods=["POST"])
@login_required
def delete_account():
    form = DeleteAccountForm()
    if not form.validate_on_submit() or not bcrypt.check_password_hash(
        current_user.password_hash,
        form.password.data,
    ):
        flash(tr("flash.delete_password_required"), "danger")
        return redirect(url_for("auth.settings"))

    user = db.session.get(User, current_user.id)
    logout_user()
    if user:
        db.session.delete(user)
        db.session.commit()

    flash(tr("flash.account_deleted"), "info")
    return redirect(url_for("main.index"))
