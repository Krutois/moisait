import logging
import os

from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix

from admin import init_admin
from config import DevelopmentConfig, ProductionConfig
from extensions import bcrypt, csrf, db, limiter, login_manager, migrate
from translations import DEFAULT_LANG, SUPPORTED_LANGS, TRANSLATIONS


def create_app(config_overrides=None):
    app = Flask(__name__)
    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=1,
        x_proto=1,
        x_host=1,
        x_port=1,
        x_prefix=1,
    )

    env = os.getenv("FLASK_ENV", "development").lower()
    if env == "production":
        ProductionConfig.init_app()
        app.config.from_object(ProductionConfig)
    else:
        app.config.from_object(DevelopmentConfig)

    if config_overrides:
        app.config.update(config_overrides)

    logging.basicConfig(level=logging.INFO)

    db.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please sign in to continue."
    login_manager.login_message_category = "warning"

    from models import User

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return db.session.get(User, int(user_id))
        except (TypeError, ValueError):
            return None

    @login_manager.unauthorized_handler
    def unauthorized():
        lang = session.get("lang", DEFAULT_LANG)
        message = TRANSLATIONS.get(lang, {}).get(
            "flash.login_required",
            TRANSLATIONS[DEFAULT_LANG].get("flash.login_required", "Please sign in to continue."),
        )
        if request.path.startswith("/api/"):
            return jsonify({"ok": False, "error": message}), 401
        flash(message, "warning")
        return redirect(url_for("auth.login", next=request.full_path))

    @app.context_processor
    def inject_i18n():
        def get_lang():
            lang = session.get("lang", DEFAULT_LANG)
            return lang if lang in SUPPORTED_LANGS else DEFAULT_LANG

        def t(key):
            lang = get_lang()
            return TRANSLATIONS.get(lang, {}).get(
                key,
                TRANSLATIONS[DEFAULT_LANG].get(key, key),
            )

        return {
            "t": t,
            "current_lang": get_lang(),
            "supported_langs": SUPPORTED_LANGS,
            "support_email": app.config.get("SUPPORT_EMAIL"),
        }

    from routes.api import bp as api_bp
    from routes.auth import bp as auth_bp
    from routes.main import bp as main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)

    import cli

    cli.init_app(app)

    init_admin(app)

    if app.config.get("AUTO_CREATE_DB", True):
        with app.app_context():
            try:
                db.create_all()
            except Exception as exc:
                app.logger.warning("Database auto-create skipped: %s", exc)

    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith("/api/"):
            return jsonify({"ok": False, "error": "Not found"}), 404
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        app.logger.exception("Unhandled server error")
        if request.path.startswith("/api/"):
            return jsonify({"ok": False, "error": "Internal server error"}), 500
        return render_template("500.html"), 500

    @app.errorhandler(Exception)
    def handle_exception(error):
        if isinstance(error, HTTPException):
            if request.path.startswith("/api/"):
                return jsonify({"ok": False, "error": error.description}), error.code
            return error
        return internal_error(error)

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), geolocation=()")
        return response

    return app
