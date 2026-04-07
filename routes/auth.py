from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db, bcrypt, limiter
from models import User
from forms import RegistrationForm, LoginForm, SettingsForm

bp = Blueprint('auth', __name__)

# ------------------- Регистрация -------------------
@bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("3 per minute")
def register():
    """Регистрация нового пользователя"""
    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data
        
        # Проверка уникальности
        if User.query.filter_by(username=username).first():
            flash('Имя пользователя уже существует', 'danger')
            return redirect(url_for('auth.register'))
        if User.query.filter_by(email=email).first():
            flash('Email уже зарегистрирован', 'danger')
            return redirect(url_for('auth.register'))
        
        # Хеширование пароля и создание пользователя
        hashed = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(username=username, email=email, password_hash=hashed)
        db.session.add(user)
        db.session.commit()
        
        flash('Регистрация успешна! Войдите в систему.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('register.html', form=form)

# ------------------- Вход -------------------
@bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    """Вход в систему"""
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        user = User.query.filter_by(username=username).first()
        
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Добро пожаловать!', 'success')
            
            # Перенаправление на запрошенную страницу или профиль
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('main.profile'))
        else:
            flash('Неверное имя пользователя или пароль', 'danger')
    
    return render_template('login.html', form=form)

# ------------------- Выход -------------------
@bp.route('/logout')
@login_required
def logout():
    """Выход из системы"""
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('main.index'))

# ------------------- Настройки профиля -------------------
@bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """Страница настроек пользователя"""
    form = SettingsForm()
    
    if form.validate_on_submit():
        # Обновление имени пользователя
        if form.username.data != current_user.username:
            existing = User.query.filter_by(username=form.username.data).first()
            if existing:
                flash('Имя пользователя уже занято', 'danger')
                return redirect(url_for('auth.settings'))
            current_user.username = form.username.data
        
        # Обновление email
        if form.email.data != current_user.email:
            existing = User.query.filter_by(email=form.email.data).first()
            if existing:
                flash('Email уже используется', 'danger')
                return redirect(url_for('auth.settings'))
            current_user.email = form.email.data
        
        # Обновление пароля (если указан)
        if form.password.data:
            current_user.password_hash = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        
        db.session.commit()
        flash('Настройки сохранены', 'success')
        return redirect(url_for('main.profile'))
    
    # Заполнение формы текущими данными
    form.username.data = current_user.username
    form.email.data = current_user.email
    return render_template('settings.html', form=form)