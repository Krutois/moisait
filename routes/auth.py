from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from extensions import db, bcrypt, limiter
from models import User
from forms import RegistrationForm, LoginForm, SettingsForm

bp = Blueprint("auth", __name__)


@bp.route("/register", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.profile"))

    form = RegistrationForm()

    if form.validate_on_submit():
        username = form.username.data.strip()
        email = form.email.data.strip().lower()
        password = form.password.data

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Имя пользователя уже занято", "danger")
            return render_template("register.html", form=form)

        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash("Этот email уже используется", "danger")
            return render_template("register.html", form=form)

        password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

        user = User(
            username=username,
            email=email,
            password_hash=password_hash,
        )

        db.session.add(user)
        db.session.commit()

        flash("Аккаунт создан. Теперь войди в систему.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("15 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.profile"))

    form = LoginForm()

    if form.validate_on_submit():
        username = form.username.data.strip()
        password = form.password.data

        user = User.query.filter_by(username=username).first()

        if not user or not bcrypt.check_password_hash(user.password_hash, password):
            flash("Неверное имя пользователя или пароль", "danger")
            return render_template("login.html", form=form)

        login_user(user, remember=True)
        flash("Добро пожаловать в VoiceFlow", "success")

        next_page = request.args.get("next")
        return redirect(next_page or url_for("main.profile"))

    return render_template("login.html", form=form)


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Вы вышли из аккаунта", "info")
    return redirect(url_for("main.index"))


@bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    form = SettingsForm(obj=current_user)

    if request.method == "GET":
        form.username.data = current_user.username
        form.email.data = current_user.email

    if form.validate_on_submit():
        username = form.username.data.strip()
        email = form.email.data.strip().lower()
        password = (form.password.data or "").strip()

        existing_user = User.query.filter(
            User.username == username,
            User.id != current_user.id
        ).first()
        if existing_user:
            flash("Имя пользователя уже занято", "danger")
            return render_template("settings.html", form=form)

        existing_email = User.query.filter(
            User.email == email,
            User.id != current_user.id
        ).first()
        if existing_email:
            flash("Этот email уже используется", "danger")
            return render_template("settings.html", form=form)

        current_user.username = username
        current_user.email = email

        if password:
            current_user.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

        db.session.commit()
        flash("Настройки сохранены", "success")
        return redirect(url_for("auth.settings"))

    return render_template("settings.html", form=form)


@bp.route("/delete-account", methods=["POST"])
@login_required
def delete_account():
    user_id = current_user.id
    logout_user()

    user = User.query.get(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()

    flash("Аккаунт удален", "info")
    return redirect(url_for("main.index"))