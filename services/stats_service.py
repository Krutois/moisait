from datetime import datetime, time, timedelta, timezone

from sqlalchemy import func

from extensions import db
from models import Favorite, Transcription, UserStats, utc_now


class StatsService:
    @staticmethod
    def for_user(user_id):
        stats = UserStats.query.filter_by(user_id=user_id).first()
        if not stats:
            stats = UserStats(user_id=user_id, daily_stats={})
            db.session.add(stats)
            db.session.commit()

        total_records = Transcription.query.filter_by(user_id=user_id).count()
        favorite_records = Favorite.query.filter_by(user_id=user_id).count()
        total_words = (
            db.session.query(func.coalesce(func.sum(Transcription.word_count), 0))
            .filter(Transcription.user_id == user_id)
            .scalar()
            or 0
        )
        avg_words = int(total_words / total_records) if total_records else 0

        today = utc_now().astimezone(timezone.utc).date()
        days = [today - timedelta(days=i) for i in range(13, -1, -1)]
        daily_activity = []
        for day in days:
            start = datetime.combine(day, time.min, tzinfo=timezone.utc)
            end = start + timedelta(days=1)
            count = (
                db.session.query(func.count(Transcription.id))
                .filter(
                    Transcription.user_id == user_id,
                    Transcription.created_at >= start,
                    Transcription.created_at < end,
                )
                .scalar()
                or 0
            )
            daily_activity.append({"date": day.isoformat(), "count": count})

        most_active = max(daily_activity, key=lambda item: item["count"], default=None)
        last_session = (
            Transcription.query.filter_by(user_id=user_id)
            .order_by(Transcription.created_at.desc())
            .first()
        )

        return {
            "total_records": total_records,
            "favorite_records": favorite_records,
            "total_words": int(total_words),
            "avg_words": avg_words,
            "total_time": int(stats.total_time or 0),
            "daily_activity": daily_activity,
            "most_active_day": most_active if most_active and most_active["count"] else None,
            "last_session": last_session.to_dict() if last_session else None,
        }
