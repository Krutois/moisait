from flask import redirect, request, url_for
from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user

from extensions import db
from models import ContactMessage, Favorite, Transcription, User, UserStats
from services.security import is_safe_url


def _admin_login_redirect():
    if is_safe_url(request.full_path, allow_current_path=True):
        return redirect(url_for("auth.login", next=request.full_path))
    return redirect(url_for("auth.login"))


class SecureAdminIndexView(AdminIndexView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin

    def inaccessible_callback(self, name, **kwargs):
        return _admin_login_redirect()


class SecureModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin

    def inaccessible_callback(self, name, **kwargs):
        return _admin_login_redirect()


def init_admin(app):
    admin = Admin(
        app,
        name="SmartLecture Admin",
        index_view=SecureAdminIndexView(url="/admin"),
    )
    admin.add_view(SecureModelView(User, db))
    admin.add_view(SecureModelView(Transcription, db))
    admin.add_view(SecureModelView(Favorite, db))
    admin.add_view(SecureModelView(UserStats, db))
    admin.add_view(SecureModelView(ContactMessage, db))
    return admin
