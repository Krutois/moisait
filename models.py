from datetime import datetime, timedelta, timezone

from flask_login import UserMixin

from extensions import db


def utc_now():
    return datetime.now(timezone.utc)


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="user", nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    transcriptions = db.relationship(
        "Transcription",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan",
    )
    favorites = db.relationship(
        "Favorite",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan",
    )
    stats = db.relationship(
        "UserStats",
        backref="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    @property
    def is_admin(self):
        return self.role == "admin"

    def __repr__(self):
        return f"<User {self.username}>"


class Transcription(db.Model):
    __tablename__ = "transcriptions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(160), nullable=False, default="New recording")
    text = db.Column(db.Text, nullable=False)
    summary = db.Column(db.Text, nullable=True)
    summary_type = db.Column(db.String(50), nullable=False, default="lecture")
    keywords_json = db.Column(db.JSON, nullable=False, default=list)
    tags_json = db.Column(db.JSON, nullable=False, default=list)
    folder = db.Column(db.String(80), nullable=True, index=True)
    language = db.Column(db.String(20), default="ru-RU", nullable=False)
    source = db.Column(db.String(50), default="speech", nullable=False)
    is_pinned = db.Column(db.Boolean, default=False, nullable=False, index=True)
    duration = db.Column(db.Integer, default=0, nullable=False)
    word_count = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    favorites = db.relationship(
        "Favorite",
        backref="transcription",
        lazy=True,
        cascade="all, delete-orphan",
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.text and not self.word_count:
            self.word_count = len(self.text.split())
        if not self.title and self.text:
            self.title = self.text.strip().splitlines()[0][:120] or "New recording"

    @property
    def is_favorite(self):
        return bool(self.favorites)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "text": self.text,
            "summary": self.summary,
            "summary_type": self.summary_type,
            "keywords_json": self.keywords_json or [],
            "tags": self.tags_json or [],
            "folder": self.folder,
            "language": self.language,
            "source": self.source,
            "is_pinned": self.is_pinned,
            "duration": self.duration,
            "word_count": self.word_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_favorite": self.is_favorite,
        }

    def __repr__(self):
        return f"<Transcription {self.id}>"


class LectureSession(db.Model):
    __tablename__ = "lecture_sessions"

    id = db.Column(db.String(40), primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    caption = db.Column(db.Text, nullable=False, default="")
    text = db.Column(db.Text, nullable=False, default="")
    status = db.Column(db.String(40), nullable=False, default="ready", index=True)
    seconds = db.Column(db.Integer, nullable=False, default=0)
    words = db.Column(db.Integer, nullable=False, default=0)
    language = db.Column(db.String(20), nullable=False, default="ru-RU")
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
    expires_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: utc_now() + timedelta(hours=12),
        nullable=False,
        index=True,
    )

    owner = db.relationship("User", backref=db.backref("lecture_sessions", lazy=True))

    @property
    def is_expired(self):
        expires_at = self.expires_at
        if expires_at and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return bool(expires_at and expires_at <= utc_now())

    def public_dict(self):
        return {
            "id": self.id,
            "caption": self.caption or "",
            "status": self.status or "ready",
            "seconds": self.seconds or 0,
            "words": self.words or 0,
            "language": self.language or "ru-RU",
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }

    def owner_dict(self):
        data = self.public_dict()
        data["text"] = self.text or ""
        data["owner_id"] = self.owner_id
        return data

    def __repr__(self):
        return f"<LectureSession {self.id}>"


class Favorite(db.Model):
    __tablename__ = "favorites"
    __table_args__ = (
        db.UniqueConstraint("user_id", "transcription_id", name="uq_favorite_user_transcription"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    transcription_id = db.Column(
        db.Integer,
        db.ForeignKey("transcriptions.id"),
        nullable=False,
        index=True,
    )
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)

    def __repr__(self):
        return f"<Favorite user={self.user_id} transcription={self.transcription_id}>"


class UserStats(db.Model):
    __tablename__ = "user_stats"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    total_time = db.Column(db.Integer, default=0, nullable=False)
    total_words = db.Column(db.Integer, default=0, nullable=False)
    daily_stats = db.Column(db.JSON, default=dict, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    def __repr__(self):
        return f"<UserStats user={self.user_id}>"


class ContactMessage(db.Model):
    __tablename__ = "contact_messages"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False, index=True)
    topic = db.Column(db.String(160), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="new", nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)
    resolved_at = db.Column(db.DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<ContactMessage {self.email}>"
