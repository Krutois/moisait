import pytest

from app import create_app
from extensions import bcrypt, db
from models import User


@pytest.fixture()
def app():
    app = create_app(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "RATELIMIT_ENABLED": False,
            "SECRET_KEY": "test-secret",
        }
    )
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def create_user(username="alice", email="alice@example.com", password="password123", role="user"):
    user = User(
        username=username,
        email=email,
        role=role,
        password_hash=bcrypt.generate_password_hash(password).decode("utf-8"),
    )
    db.session.add(user)
    db.session.commit()
    return user


def login(client, username="alice", password="password123", next_url=None):
    url = "/login"
    if next_url:
        url = f"{url}?next={next_url}"
    return client.post(
        url,
        data={"username": username, "password": password},
        follow_redirects=False,
    )
