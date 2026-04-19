from flask import Flask, session
from config import DevelopmentConfig, ProductionConfig
from extensions import db, login_manager, limiter, csrf, migrate, bcrypt
from models import User
from translations import TRANSLATIONS, SUPPORTED_LANGS, DEFAULT_LANG
import os


def create_app():
    app = Flask(__name__)

    env = os.getenv("FLASK_ENV", "development").lower()
    if env == "production":
        app.config.from_object(ProductionConfig)
    else:
        app.config.from_object(DevelopmentConfig)

    db.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Сначала войдите в аккаунт"
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return User.query.get(int(user_id))
        except (TypeError, ValueError):
            return None

    @app.context_processor
    def inject_i18n():
        def get_lang():
            lang = session.get("lang", DEFAULT_LANG)
            return lang if lang in SUPPORTED_LANGS else DEFAULT_LANG

        def t(key):
            lang = get_lang()
            return TRANSLATIONS.get(lang, {}).get(
                key,
                TRANSLATIONS[DEFAULT_LANG].get(key, key)
            )

        return {
            "t": t,
            "current_lang": get_lang(),
            "supported_langs": SUPPORTED_LANGS,
        }

    from routes.auth import bp as auth_bp
    from routes.main import bp as main_bp
    from routes.api import bp as api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)
    with app.app_context():
    from models import User, Transcription, Favorite, UserStats
    db.create_all()
    @app.errorhandler(404)
    def not_found(error):
        return "<h1 style='color:white;background:#0b1020;padding:40px;font-family:Inter'>404 — Page not found</h1>", 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return "<h1 style='color:white;background:#0b1020;padding:40px;font-family:Inter'>500 — Internal server error</h1>", 500

    with app.app_context():
        db.create_all()

    return app