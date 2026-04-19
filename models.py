from datetime import datetime
from flask_login import UserMixin
from extensions import db


# =========================
# USER
# =========================
class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # relationships
    transcriptions = db.relationship(
        "Transcription",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan"
    )

    favorites = db.relationship(
        "Favorite",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan"
    )

    stats = db.relationship(
        "UserStats",
        backref="user",
        uselist=False,
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User {self.username}>"


# =========================
# TRANSCRIPTION
# =========================
class Transcription(db.Model):
    __tablename__ = "transcriptions"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    text = db.Column(db.Text, nullable=False)

    # NEW: summary fields
    summary = db.Column(db.Text, nullable=True)
    summary_type = db.Column(db.String(50), nullable=False, default="lecture")
    keywords_json = db.Column(db.JSON, nullable=False, default=list)

    language = db.Column(db.String(20), default="ru-RU", nullable=False)
    source = db.Column(db.String(50), default="demo", nullable=False)

    duration = db.Column(db.Integer, default=0, nullable=False)  # seconds
    word_count = db.Column(db.Integer, default=0, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    # relationships
    favorites = db.relationship(
        "Favorite",
        backref="transcription",
        lazy=True,
        cascade="all, delete-orphan"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # auto word count
        if self.text:
            self.word_count = len(self.text.split())

    @property
    def is_favorite(self):
        return len(self.favorites) > 0

    def to_dict(self):
        return {
            "id": self.id,
            "text": self.text,
            "summary": self.summary,
            "summary_type": self.summary_type,
            "keywords_json": self.keywords_json or [],
            "language": self.language,
            "source": self.source,
            "duration": self.duration,
            "word_count": self.word_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_favorite": self.is_favorite
        }

    def __repr__(self):
        return f"<Transcription {self.id}>"


# =========================
# FAVORITES
# =========================
class Favorite(db.Model):
    __tablename__ = "favorites"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    transcription_id = db.Column(
        db.Integer,
        db.ForeignKey("transcriptions.id"),
        nullable=False,
        index=True
    )

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Favorite user={self.user_id} transcription={self.transcription_id}>"


# =========================
# USER STATS
# =========================
class UserStats(db.Model):
    __tablename__ = "user_stats"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        unique=True
    )

    total_time = db.Column(db.Integer, default=0, nullable=False)   # seconds
    total_words = db.Column(db.Integer, default=0, nullable=False)

    # JSON example: {"2026-04-14": 1200}
    daily_stats = db.Column(db.JSON, default=dict, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<UserStats user={self.user_id}>"