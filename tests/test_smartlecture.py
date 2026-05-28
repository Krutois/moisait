from io import BytesIO

from extensions import db
from models import ContactMessage, Favorite, LectureSession, Transcription
from services.ai_service import AIService
from tests.conftest import create_user, login


def test_register_user(client):
    response = client.post(
        "/register",
        data={
            "username": "newuser",
            "email": "new@example.com",
            "password": "password123",
            "confirm": "password123",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_login_logout(client, app):
    with app.app_context():
        create_user()

    response = login(client)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")

    response = client.post("/logout", follow_redirects=False)
    assert response.status_code == 302


def test_save_transcription(client, app):
    with app.app_context():
        create_user()
    login(client)

    response = client.post("/api/history", json={"text": "hello world", "language": "en-US"})
    assert response.status_code == 201
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["data"]["word_count"] == 2


def test_lecture_session_persists_and_public_join_updates(client, app):
    with app.app_context():
        create_user()
    login(client)

    created = client.post("/api/lecture-sessions", json={"language": "en-US"})
    assert created.status_code == 201
    created_payload = created.get_json()["data"]
    assert "/lecture/join/" in created_payload["join_url"]
    assert "/lecture/qr/" in created_payload["qr_url"]

    session_id = created_payload["id"]
    updated = client.post(
        f"/api/lecture-sessions/{session_id}",
        json={"caption": "Live text", "text": "Live text", "status": "recording", "seconds": 3, "words": 2},
    )
    assert updated.status_code == 200

    public = client.get(f"/api/lecture-sessions/{session_id}")
    payload = public.get_json()["data"]
    assert payload["caption"] == "Live text"
    assert payload["status"] == "recording"
    assert payload["seconds"] == 3

    with app.app_context():
        assert db.session.get(LectureSession, session_id) is not None


def test_foreign_user_cannot_update_lecture_session(client, app):
    with app.app_context():
        owner = create_user()
        create_user("bob", "bob@example.com")
        item = LectureSession(id="session-x", owner_id=owner.id)
        db.session.add(item)
        db.session.commit()

    login(client, "bob")
    response = client.post("/api/lecture-sessions/session-x", json={"caption": "takeover"})
    assert response.status_code == 403


def test_forbid_foreign_transcription_access(client, app):
    with app.app_context():
        owner = create_user()
        create_user("bob", "bob@example.com")
        item = Transcription(user_id=owner.id, text="private note", word_count=2)
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    login(client, "bob")
    response = client.get(f"/api/history/{item_id}")
    assert response.status_code == 404


def test_delete_transcription(client, app):
    with app.app_context():
        user = create_user()
        item = Transcription(user_id=user.id, text="delete me", word_count=2)
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    login(client)
    response = client.delete(f"/api/history/{item_id}")
    assert response.status_code == 200
    assert response.get_json()["data"]["deleted"] is True


def test_favorite_toggle(client, app):
    with app.app_context():
        user = create_user()
        item = Transcription(user_id=user.id, text="star me", word_count=2)
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    login(client)
    response = client.post(f"/api/history/{item_id}/favorite", json={})
    assert response.status_code == 200
    assert response.get_json()["data"]["is_favorite"] is True

    with app.app_context():
        assert Favorite.query.count() == 1


def test_update_title_tags_folder_and_pin(client, app):
    with app.app_context():
        user = create_user()
        item = Transcription(user_id=user.id, title="Old", text="update me", word_count=2)
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    login(client)
    response = client.patch(
        f"/api/history/{item_id}",
        json={"title": "New title", "tags": ["lecture", "exam"], "folder": "Course A", "is_pinned": True},
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["data"]["title"] == "New title"
    assert payload["data"]["tags"] == ["lecture", "exam"]
    assert payload["data"]["folder"] == "Course A"
    assert payload["data"]["is_pinned"] is True


def test_export_txt(client, app):
    with app.app_context():
        user = create_user()
        item = Transcription(user_id=user.id, text="export me", word_count=2)
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    login(client)
    response = client.get(f"/api/history/{item_id}/export/txt")
    assert response.status_code == 200
    assert b"export me" in response.data


def test_export_pdf_and_docx(client, app):
    with app.app_context():
        user = create_user()
        item = Transcription(user_id=user.id, title="Export", text="export me", word_count=2)
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    login(client)
    pdf_response = client.get(f"/api/history/{item_id}/export/pdf")
    docx_response = client.get(f"/api/history/{item_id}/export/docx")

    assert pdf_response.status_code == 200
    assert pdf_response.data.startswith(b"%PDF")
    assert docx_response.status_code == 200
    assert docx_response.data.startswith(b"PK")


def test_stats_endpoint(client, app):
    with app.app_context():
        user = create_user()
        db.session.add(Transcription(user_id=user.id, text="one two three", word_count=3))
        db.session.commit()

    login(client)
    response = client.get("/api/stats")
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["data"]["total_records"] == 1
    assert payload["data"]["total_words"] == 3


def test_contact_form_saves_message(client, app):
    response = client.post(
        "/api/contact",
        json={
            "name": "Student",
            "email": "student@example.com",
            "topic": "Question",
            "message": "Please contact me about SmartLecture.",
        },
    )

    assert response.status_code == 201
    with app.app_context():
        assert ContactMessage.query.count() == 1


def test_admin_dashboard_permissions(client, app):
    with app.app_context():
        create_user()
        create_user("admin", "admin@example.com", role="admin")

    login(client)
    forbidden = client.get("/admin-dashboard")
    assert forbidden.status_code == 403

    client.post("/logout")
    login(client, "admin")
    allowed = client.get("/admin-dashboard")
    assert allowed.status_code == 200


def test_ai_fallback_without_openai_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result, error = AIService.lecture_summary_text("First sentence. Second sentence.")
    assert error is None
    assert result["summary"]


def test_audio_upload_fallback_without_openai_key(client, app, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with app.app_context():
        create_user()

    login(client)
    response = client.post(
        "/api/transcribe/audio",
        data={"audio": (BytesIO(b"not real audio"), "lecture.mp3")},
        content_type="multipart/form-data",
    )
    payload = response.get_json()

    assert response.status_code == 503
    assert payload["ok"] is False
    assert "OPENAI_API_KEY" in payload["error"]


def test_safe_redirect_after_login(client, app):
    with app.app_context():
        create_user()

    response = login(client, next_url="https://evil.example/path")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")
