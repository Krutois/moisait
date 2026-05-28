from datetime import datetime, time, timedelta, timezone

import io

import qrcode
import qrcode.image.svg
from flask import Blueprint, Response, abort, render_template, session, redirect, request, url_for
from flask_login import login_required, current_user
from sqlalchemy import func

from extensions import db
from models import ContactMessage, Favorite, LectureSession, Transcription, User, utc_now
from services.url_service import public_url_for
from translations import SUPPORTED_LANGS, DEFAULT_LANG
from routes.auth import is_safe_url

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    return render_template("index.html")


@bp.route("/about")
def about():
    return render_template("about.html")


@bp.route("/accessibility")
@bp.route("/about-accessibility")
def accessibility():
    return render_template("accessibility.html")


@bp.route("/contact")
def contact():
    return render_template("contact.html")


@bp.route("/workspace")
@login_required
def workspace():
    return render_template("workspace.html")


@bp.route("/subtitles")
@login_required
def subtitles():
    return render_template("subtitles.html")


@bp.route("/lecture")
@login_required
def lecture():
    return render_template("lecture.html")


@bp.route("/lecture/join/<session_id>")
def lecture_join(session_id):
    return render_template("lecture_join.html", session_id=session_id)


@bp.route("/lecture/qr/<session_id>")
def lecture_qr(session_id):
    item = db.session.get(LectureSession, session_id)
    if not item or item.is_expired:
        abort(404)
    join_url = public_url_for("main.lecture_join", session_id=session_id)
    factory = qrcode.image.svg.SvgPathImage
    image = qrcode.make(join_url, image_factory=factory, box_size=10, border=2)
    buffer = io.BytesIO()
    image.save(buffer)
    return Response(buffer.getvalue(), mimetype="image/svg+xml")


@bp.route("/dialog")
@login_required
def dialog():
    return render_template("dialog.html")


@bp.route("/history")
@login_required
def history():
    items = (
        Transcription.query
        .filter_by(user_id=current_user.id)
        .order_by(Transcription.created_at.desc())
        .all()
    )
    return render_template("history.html", history=items)


@bp.route("/favorites")
@login_required
def favorites():
    return render_template("history.html", favorites_only=True)


@bp.route("/profile")
@login_required
def profile():
    return render_template("profile.html")


@bp.route("/stats")
@login_required
def stats():
    return render_template("stats.html")


@bp.route("/admin-dashboard")
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        abort(403)

    today = utc_now().date()
    days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    activity = []
    for day in days:
        start = datetime.combine(day, time.min, tzinfo=timezone.utc)
        end = start + timedelta(days=1)
        count = (
            db.session.query(func.count(Transcription.id))
            .filter(Transcription.created_at >= start, Transcription.created_at < end)
            .scalar()
            or 0
        )
        activity.append({"date": day.isoformat(), "count": count})

    data = {
        "users_count": User.query.count(),
        "transcriptions_count": Transcription.query.count(),
        "favorites_count": Favorite.query.count(),
        "contact_messages_count": ContactMessage.query.count(),
        "activity_last_7_days": activity,
        "latest_users": User.query.order_by(User.created_at.desc()).limit(5).all(),
        "latest_transcriptions": Transcription.query.order_by(Transcription.created_at.desc()).limit(5).all(),
        "latest_contact_messages": ContactMessage.query.order_by(ContactMessage.created_at.desc()).limit(5).all(),
    }
    return render_template("admin_dashboard.html", dashboard=data)


@bp.route("/set-language/<lang>")
def set_language(lang):
    if lang not in SUPPORTED_LANGS:
        lang = DEFAULT_LANG

    session["lang"] = lang
    target = request.referrer
    if not is_safe_url(target):
        target = url_for("main.index")
    return redirect(target)
