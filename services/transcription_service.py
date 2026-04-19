from datetime import datetime

from extensions import db
from models import Transcription, UserStats, Favorite


class TranscriptionService:
    @staticmethod
    def save_transcription(
        user_id,
        text,
        language="ru-RU",
        duration=0,
        source="demo",
        summary_data=None
    ):
        clean_text = (text or "").strip()
        if not clean_text:
            return None

        word_count = len(clean_text.split())

        summary = None
        summary_type = "lecture"
        keywords = []

        if isinstance(summary_data, dict):
            summary = (
                summary_data.get("summary")
                or summary_data.get("structured")
                or ""
            ).strip() or None

            summary_type = (
                str(summary_data.get("summary_type") or "lecture").strip()
                or "lecture"
            )

            raw_keywords = summary_data.get("keywords") or []
            if isinstance(raw_keywords, list):
                keywords = [str(item).strip() for item in raw_keywords if str(item).strip()]

        transcription = Transcription(
            user_id=user_id,
            text=clean_text,
            summary=summary,
            summary_type=summary_type,
            keywords_json=keywords,
            language=language or "ru-RU",
            duration=max(int(duration or 0), 0),
            source=source or "demo",
            word_count=word_count,
        )

        db.session.add(transcription)

        stats = UserStats.query.filter_by(user_id=user_id).first()
        if not stats:
            stats = UserStats(
                user_id=user_id,
                total_time=0,
                total_words=0,
                daily_stats={}
            )
            db.session.add(stats)

        stats.total_time += transcription.duration
        stats.total_words += word_count

        today = datetime.utcnow().strftime("%Y-%m-%d")
        daily_stats = dict(stats.daily_stats or {})
        daily_stats[today] = daily_stats.get(today, 0) + 1
        stats.daily_stats = daily_stats

        db.session.commit()
        return transcription

    @staticmethod
    def get_user_history(
        user_id,
        page=1,
        per_page=20,
        search="",
        language="",
        source="",
        favorites_only=False
    ):
        query = Transcription.query.filter_by(user_id=user_id)

        if search:
            query = query.filter(Transcription.text.ilike(f"%{search.strip()}%"))

        if language:
            query = query.filter(Transcription.language == language)

        if source:
            query = query.filter(Transcription.source == source)

        if favorites_only:
            query = query.join(Favorite, Favorite.transcription_id == Transcription.id)
            query = query.filter(Favorite.user_id == user_id)

        query = query.order_by(Transcription.created_at.desc())

        return query.paginate(page=page, per_page=per_page, error_out=False)

    @staticmethod
    def delete_transcription(transcription_id, user_id):
        transcription = Transcription.query.filter_by(
            id=transcription_id,
            user_id=user_id
        ).first()

        if not transcription:
            return False

        stats = UserStats.query.filter_by(user_id=user_id).first()
        if stats:
            stats.total_time = max(0, int(stats.total_time or 0) - int(transcription.duration or 0))
            stats.total_words = max(0, int(stats.total_words or 0) - int(transcription.word_count or 0))

            day_key = None
            if transcription.created_at:
                day_key = transcription.created_at.strftime("%Y-%m-%d")

            if day_key and stats.daily_stats:
                daily_stats = dict(stats.daily_stats or {})
                if day_key in daily_stats:
                    daily_stats[day_key] = max(0, int(daily_stats.get(day_key, 0)) - 1)
                    if daily_stats[day_key] == 0:
                        daily_stats.pop(day_key, None)
                    stats.daily_stats = daily_stats

        db.session.delete(transcription)
        db.session.commit()
        return True

    @staticmethod
    def set_favorite(user_id, transcription_id, is_favorite):
        transcription = Transcription.query.filter_by(
            id=transcription_id,
            user_id=user_id
        ).first()

        if not transcription:
            return None

        existing = Favorite.query.filter_by(
            user_id=user_id,
            transcription_id=transcription_id
        ).first()

        if is_favorite:
            if not existing:
                favorite = Favorite(
                    user_id=user_id,
                    transcription_id=transcription_id
                )
                db.session.add(favorite)
        else:
            if existing:
                db.session.delete(existing)

        db.session.commit()

        refreshed = Favorite.query.filter_by(
            user_id=user_id,
            transcription_id=transcription_id
        ).first()

        return refreshed is not None

    @staticmethod
    def get_user_totals(user_id):
        items = Transcription.query.filter_by(user_id=user_id).all()

        total_records = len(items)
        total_words = sum(int(item.word_count or 0) for item in items)
        total_time = sum(int(item.duration or 0) for item in items)

        favorite_records = (
            db.session.query(Favorite)
            .filter(Favorite.user_id == user_id)
            .count()
        )

        return {
            "total_records": total_records,
            "favorite_records": favorite_records,
            "total_words": total_words,
            "total_time": total_time,
        }