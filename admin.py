from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user
from flask import redirect, url_for, flash
from database import db
from models import User, Transcription, Favorite, UserStats

class AdminModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin

    def inaccessible_callback(self, name, **kwargs):
        flash('Доступ запрещён. Требуются права администратора.', 'danger')
        return redirect(url_for('main.index'))

def init_admin(app):
    admin = Admin(app, name='VoiceFlow Admin', template_mode='bootstrap4', url='/admin')
    admin.add_view(AdminModelView(User, db.session))
    admin.add_view(AdminModelView(Transcription, db.session))
    admin.add_view(AdminModelView(Favorite, db.session))
    admin.add_view(AdminModelView(UserStats, db.session))
    return admin