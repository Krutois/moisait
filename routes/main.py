from flask import Blueprint, render_template
from flask_login import login_required, current_user

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')

@bp.route('/about')
def about():
    """Страница о сервисе"""
    return render_template('about.html')

@bp.route('/contact')
def contact():
    """Страница контактов"""
    return render_template('contact.html')

@bp.route('/demo')
@login_required
def demo():
    """Демо-режим распознавания речи"""
    return render_template('demo.html')

@bp.route('/subtitles')
@login_required
def subtitles():
    """Режим субтитров (полноэкранный)"""
    return render_template('subtitles.html')

@bp.route('/dialog')
@login_required
def dialog():
    """Режим диалога (два спикера)"""
    return render_template('dialog.html')

@bp.route('/stats')
@login_required
def stats():
    """Страница статистики пользователя"""
    return render_template('stats.html')

@bp.route('/profile')
@login_required
def profile():
    """Личный кабинет пользователя"""
    return render_template('profile.html', user=current_user)

@bp.route('/history')
@login_required
def history():
    """История транскрипций"""
    return render_template('history.html')