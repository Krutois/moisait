from datetime import datetime, timedelta
from io import BytesIO
import os
import textwrap

from flask import Blueprint, request, jsonify, Response, send_file
from flask_login import login_required, current_user
from sqlalchemy import func

from extensions import limiter, db, csrf
from services.transcription_service import TranscriptionService
from services.ai_service import AIService
from models import Favorite, Transcription, UserStats, User

bp = Blueprint("api", __name__, url_prefix="/api")


def _build_export_content(transcription):
    lines = [
        "VoiceFlow Export",
        f"ID: {transcription.id}",
        f"Date: {transcription.created_at.strftime('%Y-%m-%d %H:%M') if transcription.created_at else '-'}",
        f"Language: {transcription.language or '-'}",
        f"Source: {transcription.source or '-'}",
        f"Words: {transcription.word_count or 0}",
        f"Duration: {transcription.duration or 0} sec",
        "",
        "Original text:",
        transcription.text or "",
    ]

    if transcription.summary:
        lines.extend([
            "",
            "Saved summary:",
            transcription.summary
        ])

    if transcription.keywords_json:
        lines.extend([
            "",
            "Keywords:",
            ", ".join(transcription.keywords_json)
        ])

    return "\n".join(lines)


def _find_unicode_font():
    candidates = [
        os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "arial.ttf"),
        os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "calibri.ttf"),
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/Library/Fonts/Arial.ttf",
    ]

    for path in candidates:
        if os.path.exists(path):
            return path

    return None


@bp.route("/transcribe", methods=["POST"])
@bp.route("/history", methods=["POST"])
@limiter.limit("20 per minute")
@login_required
@csrf.exempt
def save_transcription():
    data = request.get_json(silent=True) or {}

    text = (data.get("text") or "").strip()
    language = data.get("language", "ru-RU")
    duration = int(data.get("duration", 0) or 0)
    source = data.get("source", "demo")
    summary_data = data.get("summary_data")

    if not text:
        return jsonify({"error": "No text provided"}), 400

    transcription = TranscriptionService.save_transcription(
        user_id=current_user.id,
        text=text,
        language=language,
        duration=duration,
        source=source,
        summary_data=summary_data,
    )

    if not transcription:
        return jsonify({"error": "Save failed"}), 400

    return jsonify({
        "status": "saved",
        "id": transcription.id,
        "item": transcription.to_dict()
    }), 201


@bp.route("/history", methods=["GET"])
@login_required
def get_history():
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    search = request.args.get("search", "").strip()
    language = request.args.get("language", "").strip()
    source = request.args.get("source", "").strip()
    favorites_only = request.args.get("favorites_only", "").lower() in {"1", "true", "yes"}

    pagination = TranscriptionService.get_user_history(
        user_id=current_user.id,
        page=page,
        per_page=per_page,
        search=search,
        language=language,
        source=source,
        favorites_only=favorites_only,
    )

    return jsonify({
        "items": [item.to_dict() for item in pagination.items],
        "total": pagination.total,
        "page": page,
        "per_page": per_page,
        "pages": pagination.pages,
    })


@bp.route("/history/<int:item_id>", methods=["DELETE"])
@login_required
@csrf.exempt
def delete_transcription(item_id):
    if TranscriptionService.delete_transcription(item_id, current_user.id):
        return jsonify({"status": "deleted"})
    return jsonify({"error": "Not found or unauthorized"}), 404


@bp.route("/history/<int:item_id>/favorite", methods=["POST"])
@login_required
@csrf.exempt
def toggle_favorite(item_id):
    transcription = Transcription.query.filter_by(
        id=item_id,
        user_id=current_user.id
    ).first_or_404()

    data = request.get_json(silent=True) or {}
    target_state = data.get("is_favorite")

    favorite = Favorite.query.filter_by(
        user_id=current_user.id,
        transcription_id=transcription.id
    ).first()

    if target_state is True and not favorite:
        db.session.add(Favorite(
            user_id=current_user.id,
            transcription_id=transcription.id
        ))
        db.session.commit()

    elif target_state is False and favorite:
        db.session.delete(favorite)
        db.session.commit()

    elif target_state is None:
        if favorite:
            db.session.delete(favorite)
        else:
            db.session.add(Favorite(
                user_id=current_user.id,
                transcription_id=transcription.id
            ))
        db.session.commit()

    is_favorite = Favorite.query.filter_by(
        user_id=current_user.id,
        transcription_id=transcription.id
    ).first() is not None

    return jsonify({
        "status": "ok",
        "is_favorite": is_favorite
    })


@bp.route("/favorites", methods=["GET"])
@login_required
def get_favorites():
    favorites = (
        Favorite.query
        .filter_by(user_id=current_user.id)
        .order_by(Favorite.created_at.desc())
        .all()
    )

    return jsonify([
        {
            "id": fav.id,
            "transcription_id": fav.transcription_id,
            "text": fav.transcription.text,
            "summary": fav.transcription.summary,
            "summary_type": fav.transcription.summary_type,
            "keywords_json": fav.transcription.keywords_json or [],
            "language": fav.transcription.language,
            "source": fav.transcription.source,
            "created_at": fav.created_at.isoformat(),
        }
        for fav in favorites
    ])


@bp.route("/history/<int:item_id>/export/txt", methods=["GET"])
@bp.route("/export/<int:item_id>/txt", methods=["GET"])
@login_required
def export_text(item_id):
    transcription = Transcription.query.filter_by(
        id=item_id,
        user_id=current_user.id
    ).first_or_404()

    content = _build_export_content(transcription)

    response = Response(
        content,
        status=200,
        mimetype="text/plain; charset=utf-8",
    )
    response.headers["Content-Disposition"] = (
        f'attachment; filename="transcript_{item_id}.txt"'
    )
    return response


@bp.route("/history/<int:item_id>/export", methods=["GET"])
@bp.route("/history/<int:item_id>/export/pdf", methods=["GET"])
@bp.route("/export/<int:item_id>", methods=["GET"])
@bp.route("/export/<int:item_id>/pdf", methods=["GET"])
@login_required
def export_pdf(item_id):
    transcription = Transcription.query.filter_by(
        id=item_id,
        user_id=current_user.id
    ).first_or_404()

    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError:
        return jsonify({
            "error": "reportlab is not installed. Run: pip install reportlab"
        }), 500

    font_path = _find_unicode_font()
    if not font_path:
        return jsonify({
            "error": "Unicode font not found. Install Arial or DejaVu Sans."
        }), 500

    font_name = "VoiceFlowUnicode"
    if font_name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(font_name, font_path))

    content = _build_export_content(transcription)

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    left_margin = 50
    top_margin = height - 50
    bottom_margin = 50
    font_size = 11

    usable_width = width - (left_margin * 2)
    approx_chars = max(40, int(usable_width / (font_size * 0.55)))

    text_object = pdf.beginText(left_margin, top_margin)
    text_object.setFont(font_name, font_size)
    text_object.setLeading(16)

    for raw_line in content.splitlines():
        wrapped_lines = textwrap.wrap(
            raw_line,
            width=approx_chars,
            replace_whitespace=False,
            drop_whitespace=False
        ) or [""]

        for line in wrapped_lines:
            if text_object.getY() <= bottom_margin:
                pdf.drawText(text_object)
                pdf.showPage()
                text_object = pdf.beginText(left_margin, top_margin)
                text_object.setFont(font_name, font_size)
                text_object.setLeading(16)

            text_object.textLine(line)

    pdf.drawText(text_object)
    pdf.save()

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"transcript_{item_id}.pdf",
        mimetype="application/pdf"
    )


@bp.route("/ai/correct", methods=["POST"])
@limiter.limit("10 per minute")
@login_required
@csrf.exempt
def ai_correct():
    data = request.get_json(silent=True) or {}
    result, error = AIService.correct_text(data.get("text", ""))

    if error:
        return jsonify({"error": error}), 400

    return jsonify({"result": result})


@bp.route("/ai/paraphrase", methods=["POST"])
@limiter.limit("10 per minute")
@login_required
@csrf.exempt
def ai_paraphrase():
    data = request.get_json(silent=True) or {}
    result, error = AIService.paraphrase_text(data.get("text", ""))

    if error:
        return jsonify({"error": error}), 400

    return jsonify({"result": result})


@bp.route("/ai/translate", methods=["POST"])
@limiter.limit("10 per minute")
@login_required
@csrf.exempt
def ai_translate():
    data = request.get_json(silent=True) or {}
    result, error = AIService.translate_text(
        data.get("text", ""),
        data.get("target", "ru")
    )

    if error:
        return jsonify({"error": error}), 400

    return jsonify({"result": result})


@bp.route("/ai/summarize", methods=["POST"])
@limiter.limit("10 per minute")
@login_required
@csrf.exempt
def ai_summarize():
    data = request.get_json(silent=True) or {}
    result, error = AIService.summarize_text(data.get("text", ""))

    if error:
        return jsonify({"error": error}), 400

    return jsonify({"result": result})


@bp.route("/ai/lecture-summary", methods=["POST"])
@limiter.limit("10 per minute")
@login_required
@csrf.exempt
def lecture_summary():
    data = request.get_json(silent=True) or {}

    text = (data.get("text") or "").strip()
    summary_type = (data.get("summary_type") or "lecture").strip()

    allowed_types = {"lecture", "short", "bullets", "exam", "terms"}
    if summary_type not in allowed_types:
        summary_type = "lecture"

    if not text:
        return jsonify({"error": "Text is required"}), 400

    result, error = AIService.lecture_summary_text(
        text,
        summary_type=summary_type
    )

    if error:
        return jsonify({"error": error}), 400

    return jsonify(result)


@bp.route("/ai/study-mode", methods=["POST"])
@limiter.limit("10 per minute")
@login_required
@csrf.exempt
def ai_study_mode():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()

    if not text:
        return jsonify({"error": "Text is required"}), 400

    result, error = AIService.study_mode_text(text)
    if error:
        return jsonify({"error": error}), 400

    return jsonify(result)


@bp.route("/stats", methods=["GET"])
@login_required
def get_stats():
    stats = current_user.stats
    if not stats:
        stats = UserStats(user_id=current_user.id, daily_stats={})
        db.session.add(stats)
        db.session.commit()

    total_records = Transcription.query.filter_by(user_id=current_user.id).count()

    favorite_records = (
        db.session.query(func.count(Favorite.id))
        .filter(Favorite.user_id == current_user.id)
        .scalar()
        or 0
    )

    total_words = (
        db.session.query(func.coalesce(func.sum(Transcription.word_count), 0))
        .filter(Transcription.user_id == current_user.id)
        .scalar()
        or 0
    )

    avg_words = int(total_words / total_records) if total_records > 0 else 0

    today = datetime.utcnow().date()
    days = [today - timedelta(days=i) for i in range(6, -1, -1)]

    daily_activity = []
    for day in days:
        count = (
            db.session.query(func.count(Transcription.id))
            .filter(
                Transcription.user_id == current_user.id,
                func.date(Transcription.created_at) == day
            )
            .scalar()
            or 0
        )

        daily_activity.append({
            "date": day.strftime("%Y-%m-%d"),
            "count": count
        })

    return jsonify({
        "total_records": total_records,
        "favorite_records": favorite_records,
        "total_words": total_words,
        "avg_words": avg_words,
        "daily_activity": daily_activity
    })


@bp.route("/user", methods=["PUT"])
@login_required
@csrf.exempt
def update_user():
    data = request.get_json(silent=True) or {}

    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()

    if not username or not email:
        return jsonify({"error": "Username and email are required"}), 400

    existing_username = User.query.filter(
        User.username == username,
        User.id != current_user.id
    ).first()

    if existing_username:
        return jsonify({"error": "Username already taken"}), 400

    existing_email = User.query.filter(
        User.email == email,
        User.id != current_user.id
    ).first()

    if existing_email:
        return jsonify({"error": "Email already taken"}), 400

    current_user.username = username
    current_user.email = email
    db.session.commit()

    return jsonify({
        "status": "updated",
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
        }
    })