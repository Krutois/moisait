from flask import Blueprint, render_template, session, redirect, request, url_for
from flask_login import login_required, current_user

from models import Transcription
from translations import SUPPORTED_LANGS, DEFAULT_LANG

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    return render_template("index.html")


@bp.route("/about")
def about():
    return render_template("about.html")


@bp.route("/contact")
def contact():
    return render_template("contact.html")


@bp.route("/demo")
@login_required
def demo():
    return render_template("demo.html")


@bp.route("/subtitles")
@login_required
def subtitles():
    return render_template("subtitles.html")


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


@bp.route("/profile")
@login_required
def profile():
    return render_template("profile.html")


@bp.route("/stats")
@login_required
def stats():
    return render_template("stats.html")


@bp.route("/set-language/<lang>")
def set_language(lang):
    if lang not in SUPPORTED_LANGS:
        lang = DEFAULT_LANG

    session["lang"] = lang
    return redirect(request.referrer or url_for("main.index"))