import logging
import os

from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy import text
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix

from admin import init_admin
from config import DevelopmentConfig, ProductionConfig
from extensions import bcrypt, csrf, db, limiter, login_manager, migrate
from translations import DEFAULT_LANG, SUPPORTED_LANGS, TRANSLATIONS


def ensure_database_schema(app):
    if not app.config.get("AUTO_CREATE_DB", True):
        return

    with app.app_context():
        try:
            db.create_all()
        except Exception as exc:
            app.logger.warning("Database auto-create skipped: %s", exc)
            return

        if db.engine.dialect.name != "postgresql":
            return

        statements = [
            """
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS role VARCHAR(20) NOT NULL DEFAULT 'user'
            """,
            """
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            """,
            """
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            """,
            """
            ALTER TABLE transcriptions
            ADD COLUMN IF NOT EXISTS title VARCHAR(160) NOT NULL DEFAULT 'New recording'
            """,
            """
            ALTER TABLE transcriptions
            ADD COLUMN IF NOT EXISTS summary TEXT
            """,
            """
            ALTER TABLE transcriptions
            ADD COLUMN IF NOT EXISTS summary_type VARCHAR(50) NOT NULL DEFAULT 'lecture'
            """,
            """
            ALTER TABLE transcriptions
            ADD COLUMN IF NOT EXISTS keywords_json JSON NOT NULL DEFAULT '[]'::json
            """,
            """
            ALTER TABLE transcriptions
            ADD COLUMN IF NOT EXISTS tags_json JSON NOT NULL DEFAULT '[]'::json
            """,
            """
            ALTER TABLE transcriptions
            ADD COLUMN IF NOT EXISTS folder VARCHAR(80)
            """,
            """
            ALTER TABLE transcriptions
            ADD COLUMN IF NOT EXISTS language VARCHAR(20) NOT NULL DEFAULT 'ru-RU'
            """,
            """
            ALTER TABLE transcriptions
            ADD COLUMN IF NOT EXISTS source VARCHAR(50) NOT NULL DEFAULT 'speech'
            """,
            """
            ALTER TABLE transcriptions
            ADD COLUMN IF NOT EXISTS is_pinned BOOLEAN NOT NULL DEFAULT FALSE
            """,
            """
            ALTER TABLE transcriptions
            ADD COLUMN IF NOT EXISTS duration INTEGER NOT NULL DEFAULT 0
            """,
            """
            ALTER TABLE transcriptions
            ADD COLUMN IF NOT EXISTS word_count INTEGER NOT NULL DEFAULT 0
            """,
            """
            ALTER TABLE transcriptions
            ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            """,
            """
            ALTER TABLE transcriptions
            ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            """,
            """
            ALTER TABLE user_stats
            ADD COLUMN IF NOT EXISTS total_time INTEGER NOT NULL DEFAULT 0
            """,
            """
            ALTER TABLE user_stats
            ADD COLUMN IF NOT EXISTS total_words INTEGER NOT NULL DEFAULT 0
            """,
            """
            ALTER TABLE user_stats
            ADD COLUMN IF NOT EXISTS daily_stats JSON NOT NULL DEFAULT '{}'::json
            """,
            """
            ALTER TABLE user_stats
            ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            """,
            """
            ALTER TABLE user_stats
            ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            """,
            """
            ALTER TABLE contact_messages
            ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'new'
            """,
            """
            ALTER TABLE contact_messages
            ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            """,
            """
            ALTER TABLE contact_messages
            ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMPTZ
            """,
            """
            ALTER TABLE favorites
            ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            """,
            """
            ALTER TABLE lecture_sessions
            ADD COLUMN IF NOT EXISTS owner_id INTEGER
            """,
            """
            ALTER TABLE lecture_sessions
            ADD COLUMN IF NOT EXISTS caption TEXT NOT NULL DEFAULT ''
            """,
            """
            ALTER TABLE lecture_sessions
            ADD COLUMN IF NOT EXISTS text TEXT NOT NULL DEFAULT ''
            """,
            """
            ALTER TABLE lecture_sessions
            ADD COLUMN IF NOT EXISTS status VARCHAR(40) NOT NULL DEFAULT 'ready'
            """,
            """
            ALTER TABLE lecture_sessions
            ADD COLUMN IF NOT EXISTS seconds INTEGER NOT NULL DEFAULT 0
            """,
            """
            ALTER TABLE lecture_sessions
            ADD COLUMN IF NOT EXISTS words INTEGER NOT NULL DEFAULT 0
            """,
            """
            ALTER TABLE lecture_sessions
            ADD COLUMN IF NOT EXISTS language VARCHAR(20) NOT NULL DEFAULT 'ru-RU'
            """,
            """
            ALTER TABLE lecture_sessions
            ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            """,
            """
            ALTER TABLE lecture_sessions
            ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            """,
            """
            ALTER TABLE lecture_sessions
            ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '12 hours')
            """,
        ]

        try:
            for statement in statements:
                db.session.execute(text(statement))
            db.session.commit()
            app.logger.info("Database schema checked and updated")
        except Exception as exc:
            db.session.rollback()
            app.logger.exception("Database schema update failed: %s", exc)


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

    ensure_database_schema(app)

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
