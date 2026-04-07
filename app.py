import os
from flask import Flask, jsonify, g, send_from_directory, request, render_template
from config import DevelopmentConfig, ProductionConfig
from extensions import db, bcrypt, login_manager, csrf, limiter, migrate
from models import User
from admin import init_admin

def create_app(config_class=DevelopmentConfig):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Инициализация расширений
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    migrate.init_app(app, db)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Пожалуйста, войдите для доступа к этой странице.'
    login_manager.login_message_category = 'info'

    # Регистрация user_loader
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Регистрация blueprints
    from routes.main import bp as main_bp
    app.register_blueprint(main_bp)

    from routes.auth import bp as auth_bp
    app.register_blueprint(auth_bp)

    from routes.api import bp as api_bp
    app.register_blueprint(api_bp)

    # Админка
    init_admin(app)

    # Локализация (полный словарь LOCALES)
    LOCALES = {
        'ru': {
            'home': 'Главная', 'about': 'О сервисе', 'demo': 'Демо',
            'profile': 'Профиль', 'history': 'История', 'settings': 'Настройки',
            'login': 'Вход', 'register': 'Регистрация', 'logout': 'Выход',
            'contact': 'Контакты', 'subtitles': 'Субтитры', 'dialog': 'Диалог',
            'stats': 'Статистика', 'ai_powered': 'AI‑распознавание речи',
            'copy': 'Копировать', 'download': 'Скачать', 'clear': 'Очистить',
            'start_recording': 'Начать запись', 'stop_recording': 'Остановить',
            'speech_placeholder': 'Здесь появится распознанный текст...',
            'live_demo': 'Живая демонстрация',
            'why_voiceflow': 'Почему VoiceFlow',
            'realtime': 'Мгновенно', 'realtime_desc': 'Слова появляются по мере речи',
            'multilang': '3 языка', 'multilang_desc': 'Русский, казахский, английский',
            'private': 'Конфиденциально', 'private_desc': 'Ваши данные хранятся только у вас',
            'search_placeholder': 'Поиск...', 'all_languages': 'Все языки',
            'search': 'Поиск', 'no_history': 'Нет транскрипций',
            'delete': 'Удалить', 'favorited': 'В избранном',
            'confirm_delete': 'Удалить эту транскрипцию?',
            'previous': 'Предыдущая', 'next': 'Следующая',
            'get_in_touch': 'Свяжитесь с нами', 'contact_desc': 'Есть вопросы?',
            'project_info': 'О проекте', 'project_desc': 'Дипломный проект',
            'tech_stack': 'Технологии: Flask, SQLite, Web Speech API, Tailwind CSS',
            'accessibility': 'Доступность', 'accessibility_desc': 'Помощь людям с нарушениями слуха',
            'username': 'Имя пользователя', 'email': 'Email', 'password': 'Пароль',
            'confirm_password': 'Подтверждение пароля', 'already_account': 'Уже есть аккаунт?',
            'no_account': 'Нет аккаунта?', 'password_leave_blank': 'Оставьте пустым, чтобы не менять',
            'save_changes': 'Сохранить изменения'
        },
        'kk': {
            'home': 'Басты бет', 'about': 'Қызмет туралы', 'demo': 'Демо',
            'profile': 'Профиль', 'history': 'Тарих', 'settings': 'Баптаулар',
            'login': 'Кіру', 'register': 'Тіркелу', 'logout': 'Шығу',
            'contact': 'Байланыс', 'subtitles': 'Субтитрлер', 'dialog': 'Диалог',
            'stats': 'Статистика', 'ai_powered': 'Жасанды интеллектпен сөйлеуді тану',
            'copy': 'Көшіру', 'download': 'Жүктеу', 'clear': 'Тазалау',
            'start_recording': 'Жазуды бастау', 'stop_recording': 'Тоқтату',
            'speech_placeholder': 'Танылған мәтін осында пайда болады...',
            'live_demo': 'Тікелей демо',
            'why_voiceflow': 'Неге VoiceFlow',
            'realtime': 'Лезде', 'realtime_desc': 'Сөздер сөйлеген кезде пайда болады',
            'multilang': '3 тіл', 'multilang_desc': 'Орысша, қазақша, ағылшынша',
            'private': 'Құпия', 'private_desc': 'Деректеріңіз тек сізде сақталады',
            'search_placeholder': 'Іздеу...', 'all_languages': 'Барлық тілдер',
            'search': 'Іздеу', 'no_history': 'Жазбалар жоқ',
            'delete': 'Жою', 'favorited': 'Таңдаулыда',
            'confirm_delete': 'Бұл жазбаны жою керек пе?',
            'previous': 'Алдыңғы', 'next': 'Келесі',
            'get_in_touch': 'Бізбен байланысыңыз', 'contact_desc': 'Сұрақтарыңыз бар ма?',
            'project_info': 'Жоба туралы', 'project_desc': 'Дипломдық жоба',
            'tech_stack': 'Технологиялар: Flask, SQLite, Web Speech API, Tailwind CSS',
            'accessibility': 'Қолжетімділік', 'accessibility_desc': 'Есту қабілеті бұзылған адамдарға көмек',
            'username': 'Пайдаланушы аты', 'email': 'Электрондық пошта', 'password': 'Құпия сөз',
            'confirm_password': 'Құпия сөзді растау', 'already_account': 'Аккаунтыңыз бар ма?',
            'no_account': 'Аккаунтыңыз жоқ па?', 'password_leave_blank': 'Өзгертпеу үшін бос қалдырыңыз',
            'save_changes': 'Өзгерістерді сақтау'
        },
        'en': {
            'home': 'Home', 'about': 'About', 'demo': 'Demo',
            'profile': 'Profile', 'history': 'History', 'settings': 'Settings',
            'login': 'Login', 'register': 'Register', 'logout': 'Logout',
            'contact': 'Contact', 'subtitles': 'Subtitles', 'dialog': 'Dialogue',
            'stats': 'Statistics', 'ai_powered': 'AI‑powered speech recognition',
            'copy': 'Copy', 'download': 'Download', 'clear': 'Clear',
            'start_recording': 'Start Recording', 'stop_recording': 'Stop',
            'speech_placeholder': 'Your transcribed text will appear here...',
            'live_demo': 'Live Demo',
            'why_voiceflow': 'Why VoiceFlow',
            'realtime': 'Real‑time', 'realtime_desc': 'Words appear as you speak',
            'multilang': '3 Languages', 'multilang_desc': 'Russian, Kazakh, English',
            'private': 'Private', 'private_desc': 'Your data stays with you',
            'search_placeholder': 'Search...', 'all_languages': 'All languages',
            'search': 'Search', 'no_history': 'No transcriptions',
            'delete': 'Delete', 'favorited': 'Favorited',
            'confirm_delete': 'Delete this transcription?',
            'previous': 'Previous', 'next': 'Next',
            'get_in_touch': 'Get in touch', 'contact_desc': 'Have questions?',
            'project_info': 'Project info', 'project_desc': 'Graduation project',
            'tech_stack': 'Technologies: Flask, SQLite, Web Speech API, Tailwind CSS',
            'accessibility': 'Accessibility', 'accessibility_desc': 'Helping hearing impaired',
            'username': 'Username', 'email': 'Email', 'password': 'Password',
            'confirm_password': 'Confirm Password', 'already_account': 'Already have an account?',
            'no_account': 'No account?', 'password_leave_blank': 'Leave blank to keep current',
            'save_changes': 'Save changes'
        }
    }

    @app.before_request
    def set_language():
        lang = request.cookies.get('lang', 'ru')
        if lang not in LOCALES:
            lang = 'ru'
        g.lang = lang
        g.locale = LOCALES[lang]

    @app.context_processor
    def inject_locale():
        return {'locale': g.locale, 'lang': g.lang}

    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify(error="Слишком много запросов. Попробуйте позже."), 429

    @app.errorhandler(404)
    def not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        app.logger.error(f'Server error: {e}')
        return render_template('500.html'), 500

    # PWA
    @app.route('/manifest.json')
    def manifest():
        return send_from_directory('static', 'manifest.json')

    @app.route('/sw.js')
    def sw():
        return send_from_directory('static', 'sw.js'), 200, {'Content-Type': 'application/javascript'}

    return app