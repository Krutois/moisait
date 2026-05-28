from datetime import timedelta
from uuid import uuid4

from flask import Blueprint, Response, current_app, jsonify, request, send_file, session, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from email_validator import EmailNotValidError, validate_email

from extensions import db, limiter
from models import ContactMessage, Favorite, LectureSession, Transcription, utc_now
from services.ai_service import AIService
from services.audio_service import AudioService
from services.export_service import ExportService
from services.stats_service import StatsService
from services.transcription_service import TranscriptionService
from services.url_service import public_url_for
from translations import DEFAULT_LANG, TRANSLATIONS

bp = Blueprint("api", __name__, url_prefix="/api")


def ok(data=None, status=200):
    return jsonify({"ok": True, "data": data if data is not None else {}}), status


def fail(message, status=400):
    return jsonify({"ok": False, "error": message}), status


def tr(key):
    lang = session.get("lang", DEFAULT_LANG)
    return TRANSLATIONS.get(lang, {}).get(key, TRANSLATIONS[DEFAULT_LANG].get(key, key))


def localize_service_error(error):
    if not error:
        return error
    if "OPENAI_API_KEY" in error:
        return tr("api.openai_key_missing")
    mapping = {
        "OpenAI package is not installed": "api.openai_package_missing",
        "OpenAI quota exceeded": "api.openai_quota_exceeded",
        "OpenAI API key is invalid": "api.openai_key_invalid",
        "OpenAI rate limit reached": "api.openai_rate_limit",
        "OpenAI rejected the audio request": "api.openai_audio_rejected",
        "Audio transcription failed": "api.audio_transcription_failed",
        "AI client is unavailable": "api.ai_client_unavailable",
        "Empty AI response": "api.ai_empty_response",
        "Empty text": "api.text_required",
    }
    return tr(mapping.get(error, error))


def get_json():
    data = request.get_json(silent=True)
    if data is None:
        return {}
    if not isinstance(data, dict):
        return None
    return data


def owned_transcription(item_id):
    return Transcription.query.filter_by(id=item_id, user_id=current_user.id).first()


def is_teacher_user():
    return current_user.is_authenticated and current_user.role in {"teacher", "admin"}


def can_update_lecture_session(item):
    return current_user.is_authenticated and (item.owner_id == current_user.id or is_teacher_user())


def clean_session_id(session_id):
    return "".join(ch for ch in str(session_id) if ch.isalnum() or ch in {"-", "_"})[:40]


@bp.route("/lecture-sessions", methods=["POST"])
@login_required
def create_lecture_session():
    session_id = uuid4().hex
    item = LectureSession(
        id=session_id,
        owner_id=current_user.id,
        status="ready",
        language=(get_json() or {}).get("language", "ru-RU"),
        expires_at=utc_now() + timedelta(hours=12),
    )
    db.session.add(item)
    db.session.commit()
    return ok(
        {
            "id": session_id,
            "join_url": public_url_for("main.lecture_join", session_id=session_id),
            "qr_url": public_url_for("main.lecture_qr", session_id=session_id),
        },
        201,
    )


@bp.route("/lecture-sessions/<session_id>", methods=["POST"])
@login_required
def update_lecture_session(session_id):
    item = db.session.get(LectureSession, clean_session_id(session_id))
    if not item:
        return fail(tr("api.lecture_session_not_found"), 404)
    if item.is_expired:
        return fail(tr("api.lecture_session_expired"), 410)
    if not can_update_lecture_session(item):
        return fail(tr("api.forbidden"), 403)
    data = get_json()
    if data is None:
        return fail(tr("api.invalid_json"), 400)
    for key in ("caption", "text", "status", "language"):
        if key in data:
            setattr(item, key, str(data.get(key) or "")[:200000])
    for key in ("seconds", "words"):
        if key in data:
            setattr(item, key, max(int(data.get(key) or 0), 0))
    db.session.commit()
    return ok(item.owner_dict())


@bp.route("/lecture-sessions/<session_id>", methods=["GET"])
def get_lecture_session(session_id):
    item = db.session.get(LectureSession, clean_session_id(session_id))
    if not item:
        return fail(tr("api.lecture_session_not_found"), 404)
    if item.is_expired:
        return fail(tr("api.lecture_session_expired"), 410)
    return ok(item.public_dict())


@bp.route("/history", methods=["POST"])
@limiter.limit("20 per minute")
@login_required
def save_transcription():
    data = get_json()
    if data is None:
        return fail(tr("api.invalid_json"), 400)

    text = (data.get("text") or "").strip()
    if not text:
        return fail(tr("api.text_required"), 400)
    if len(text) > 200000:
        return fail(tr("api.text_too_long"), 413)

    tags = data.get("tags") or []
    if isinstance(tags, str):
        tags = [item.strip() for item in tags.split(",") if item.strip()]
    if not isinstance(tags, list):
        return fail(tr("api.tags_list"), 400)

    try:
        transcription = TranscriptionService.save_transcription(
            user_id=current_user.id,
            title=data.get("title"),
            text=text,
            language=data.get("language", "ru-RU"),
            duration=int(data.get("duration", 0) or 0),
            source=data.get("source", "speech"),
            summary_data=data.get("summary_data"),
            tags=tags,
            folder=data.get("folder"),
        )
    except Exception:
        current_app.logger.exception("Failed to save transcription")
        db.session.rollback()
        return fail(tr("api.save_failed"), 500)

    return ok(transcription.to_dict(), 201)


@bp.route("/transcribe", methods=["POST"])
@login_required
def transcribe_alias():
    return save_transcription()


@bp.route("/history", methods=["GET"])
@login_required
def get_history():
    pagination = TranscriptionService.get_user_history(
        user_id=current_user.id,
        page=max(request.args.get("page", 1, type=int), 1),
        per_page=min(max(request.args.get("per_page", 20, type=int), 1), 100),
        search=request.args.get("search", "").strip(),
        language=request.args.get("language", "").strip(),
        source=request.args.get("source", "").strip(),
        folder=request.args.get("folder", "").strip(),
        tag=request.args.get("tag", "").strip(),
        favorites_only=request.args.get("favorites_only", "").lower() in {"1", "true", "yes"},
        pinned_only=request.args.get("pinned_only", "").lower() in {"1", "true", "yes"},
    )
    return ok(
        {
            "items": [item.to_dict() for item in pagination.items],
            "total": pagination.total,
            "page": pagination.page,
            "per_page": pagination.per_page,
            "pages": pagination.pages,
        }
    )


@bp.route("/history/<int:item_id>", methods=["GET"])
@login_required
def get_history_item(item_id):
    transcription = owned_transcription(item_id)
    if not transcription:
        return fail(tr("api.not_found"), 404)
    return ok(transcription.to_dict())


@bp.route("/history/<int:item_id>", methods=["PATCH"])
@login_required
def update_history_item(item_id):
    data = get_json()
    if data is None:
        return fail(tr("api.invalid_json"), 400)
    transcription = TranscriptionService.update_transcription(current_user.id, item_id, **data)
    if not transcription:
        return fail(tr("api.not_found"), 404)
    return ok(transcription.to_dict())


@bp.route("/history/<int:item_id>", methods=["DELETE"])
@login_required
def delete_transcription(item_id):
    if TranscriptionService.delete_transcription(item_id, current_user.id):
        return ok({"deleted": True})
    return fail(tr("api.not_found"), 404)


@bp.route("/history/<int:item_id>/favorite", methods=["POST"])
@login_required
def toggle_favorite(item_id):
    data = get_json()
    if data is None:
        return fail(tr("api.invalid_json"), 400)

    transcription = owned_transcription(item_id)
    if not transcription:
        return fail(tr("api.not_found"), 404)

    target_state = data.get("is_favorite")
    if target_state is None:
        target_state = Favorite.query.filter_by(
            user_id=current_user.id,
            transcription_id=transcription.id,
        ).first() is None

    is_favorite = TranscriptionService.set_favorite(
        current_user.id,
        transcription.id,
        bool(target_state),
    )
    return ok({"is_favorite": is_favorite})


@bp.route("/history/<int:item_id>/export/txt", methods=["GET"])
@login_required
def export_txt(item_id):
    transcription = owned_transcription(item_id)
    if not transcription:
        return fail(tr("api.not_found"), 404)
    content = ExportService.txt(transcription, session.get("lang", DEFAULT_LANG))
    response = Response(content, mimetype="text/plain; charset=utf-8")
    response.headers["Content-Disposition"] = f'attachment; filename="smartlecture_{item_id}.txt"'
    return response


@bp.route("/history/<int:item_id>/export/pdf", methods=["GET"])
@login_required
def export_pdf(item_id):
    transcription = owned_transcription(item_id)
    if not transcription:
        return fail(tr("api.not_found"), 404)
    try:
        buffer = ExportService.pdf(transcription, session.get("lang", DEFAULT_LANG))
    except Exception:
        current_app.logger.exception("PDF export failed")
        return fail(tr("api.pdf_export_failed"), 500)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"smartlecture_{item_id}.pdf",
        mimetype="application/pdf",
    )


@bp.route("/history/<int:item_id>/export/docx", methods=["GET"])
@login_required
def export_docx(item_id):
    transcription = owned_transcription(item_id)
    if not transcription:
        return fail(tr("api.not_found"), 404)
    try:
        buffer = ExportService.docx(transcription, session.get("lang", DEFAULT_LANG))
    except Exception:
        current_app.logger.exception("DOCX export failed")
        return fail(tr("api.docx_export_failed"), 500)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"smartlecture_{item_id}.docx",
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@bp.route("/export/<int:item_id>/txt", methods=["GET"])
@bp.route("/export/<int:item_id>", methods=["GET"])
@login_required
def legacy_export_txt(item_id):
    return export_txt(item_id)


@bp.route("/export/<int:item_id>/pdf", methods=["GET"])
@login_required
def legacy_export_pdf(item_id):
    return export_pdf(item_id)


def ai_response(result, error):
    if error:
        return fail(localize_service_error(error), 400)
    return ok(result)


@bp.route("/ai/correct", methods=["POST"])
@limiter.limit("10 per minute")
@login_required
def ai_correct():
    data = get_json()
    if data is None:
        return fail(tr("api.invalid_json"), 400)
    return ai_response(*AIService.correct_text(data.get("text", "")))


@bp.route("/ai/paraphrase", methods=["POST"])
@limiter.limit("10 per minute")
@login_required
def ai_paraphrase():
    data = get_json()
    if data is None:
        return fail(tr("api.invalid_json"), 400)
    return ai_response(*AIService.paraphrase_text(data.get("text", "")))


@bp.route("/ai/translate", methods=["POST"])
@limiter.limit("10 per minute")
@login_required
def ai_translate():
    data = get_json()
    if data is None:
        return fail(tr("api.invalid_json"), 400)
    return ai_response(*AIService.translate_text(data.get("text", ""), data.get("target", "ru")))


@bp.route("/ai/summarize", methods=["POST"])
@limiter.limit("10 per minute")
@login_required
def ai_summarize():
    data = get_json()
    if data is None:
        return fail(tr("api.invalid_json"), 400)
    return ai_response(*AIService.summarize_text(data.get("text", "")))


@bp.route("/ai/lecture-summary", methods=["POST"])
@limiter.limit("10 per minute")
@login_required
def lecture_summary():
    data = get_json()
    if data is None:
        return fail(tr("api.invalid_json"), 400)

    text = (data.get("text") or "").strip()
    if not text:
        return fail(tr("api.text_required"), 400)
    if len(text) > current_app.config.get("AI_MAX_INPUT_CHARS", 20000):
        return fail(tr("api.ai_text_too_long"), 413)

    result, error = AIService.lecture_summary_text(text, data.get("summary_type", "lecture"))
    return ai_response(result, error)


@bp.route("/ai/study-mode", methods=["POST"])
@limiter.limit("10 per minute")
@login_required
def ai_study_mode():
    data = get_json()
    if data is None:
        return fail(tr("api.invalid_json"), 400)

    text = (data.get("text") or "").strip()
    if not text:
        return fail(tr("api.text_required"), 400)
    if len(text) > current_app.config.get("AI_MAX_INPUT_CHARS", 20000):
        return fail(tr("api.ai_text_too_long"), 413)

    result, error = AIService.study_mode_text(text)
    return ai_response(result, error)


@bp.route("/transcribe/audio", methods=["POST"])
@bp.route("/audio/transcribe", methods=["POST"])
@limiter.limit("5 per minute")
@login_required
def transcribe_audio():
    file_storage = request.files.get("audio")
    if not file_storage or not file_storage.filename:
        return fail(tr("api.audio_required"), 400)

    filename = secure_filename(file_storage.filename)
    if not AudioService.is_allowed(filename):
        return fail(tr("api.audio_formats"), 400)

    text, error = AudioService.transcribe(file_storage, current_app.config.get("OPENAI_AUDIO_MODEL"))
    if error:
        status = 500
        if "OPENAI_API_KEY" in error:
            status = 503
        elif error == "OpenAI quota exceeded":
            status = 402
        elif error == "OpenAI rate limit reached":
            status = 429
        elif error == "OpenAI API key is invalid":
            status = 401
        elif error == "OpenAI rejected the audio request":
            status = 400
        return fail(localize_service_error(error), status)
    return ok({"text": text, "filename": filename})


@bp.route("/stats", methods=["GET"])
@login_required
def get_stats():
    return ok(StatsService.for_user(current_user.id))


@bp.route("/contact", methods=["POST"])
@limiter.limit("5 per minute")
def contact_message():
    data = get_json()
    if data is None:
        return fail(tr("api.invalid_json"), 400)

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    topic = (data.get("topic") or "").strip()
    message = (data.get("message") or "").strip()
    if not all([name, email, topic, message]):
        return fail(tr("api.all_fields_required"), 400)
    try:
        validate_email(email, check_deliverability=False)
    except EmailNotValidError:
        return fail(tr("api.email_invalid"), 400)
    if len(message) > 5000:
        return fail(tr("api.message_too_long"), 413)

    db.session.add(ContactMessage(name=name[:120], email=email[:120], topic=topic[:160], message=message))
    db.session.commit()
    return ok({"saved": True}, 201)
