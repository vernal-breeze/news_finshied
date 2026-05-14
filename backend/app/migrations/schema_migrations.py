"""
数据库 Schema 迁移
确保数据库表结构与模型定义一致
"""
from sqlalchemy import inspect, text

from app.database import engine, Base, SessionLocal
from app.core.logging_config import get_logger


def _ensure_columns(table_name: str, statements_by_column: dict[str, str]) -> None:
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
    statements = [sql for column, sql in statements_by_column.items() if column not in existing_columns]
    if not statements:
        return

    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))


def _ensure_clue_columns() -> None:
    _ensure_columns(
        "clues",
        {
            "source_url": "ALTER TABLE clues ADD COLUMN source_url VARCHAR",
            "keywords": "ALTER TABLE clues ADD COLUMN keywords TEXT",
            "news_value_score": "ALTER TABLE clues ADD COLUMN news_value_score FLOAT NOT NULL DEFAULT 0",
            "propagation_potential": "ALTER TABLE clues ADD COLUMN propagation_potential FLOAT NOT NULL DEFAULT 0",
            "creator_id": "ALTER TABLE clues ADD COLUMN creator_id INTEGER",
            "channel": "ALTER TABLE clues ADD COLUMN channel VARCHAR(50) DEFAULT ''",
            "processed_at": "ALTER TABLE clues ADD COLUMN processed_at DATETIME",
        },
    )


def _ensure_topic_columns() -> None:
    _ensure_columns(
        "topics",
        {
            "category": "ALTER TABLE topics ADD COLUMN category VARCHAR",
            "editor": "ALTER TABLE topics ADD COLUMN editor VARCHAR",
            "planned_date": "ALTER TABLE topics ADD COLUMN planned_date DATETIME",
            "ai_score": "ALTER TABLE topics ADD COLUMN ai_score FLOAT",
            "performance_score": "ALTER TABLE topics ADD COLUMN performance_score FLOAT",
            "assigned_user_id": "ALTER TABLE topics ADD COLUMN assigned_user_id INTEGER",
            "ai_suggestion": "ALTER TABLE topics ADD COLUMN ai_suggestion TEXT",
            "ref_clue_ids": "ALTER TABLE topics ADD COLUMN ref_clue_ids TEXT",
            "updated_at": "ALTER TABLE topics ADD COLUMN updated_at DATETIME",
        },
    )


def _ensure_article_columns() -> None:
    _ensure_columns(
        "articles",
        {
            "clue_id": "ALTER TABLE articles ADD COLUMN clue_id INTEGER",
            "topic_id": "ALTER TABLE articles ADD COLUMN topic_id INTEGER",
            "reject_reason": "ALTER TABLE articles ADD COLUMN reject_reason VARCHAR(1000) DEFAULT ''",
        },
    )


def _ensure_feedback_columns() -> None:
    _ensure_columns(
        "feedback",
        {
            "article_id": "ALTER TABLE feedback ADD COLUMN article_id INTEGER",
            "content": "ALTER TABLE feedback ADD COLUMN content TEXT",
            "view_count": "ALTER TABLE feedback ADD COLUMN view_count INTEGER NOT NULL DEFAULT 0",
            "like_count": "ALTER TABLE feedback ADD COLUMN like_count INTEGER NOT NULL DEFAULT 0",
            "comment_count": "ALTER TABLE feedback ADD COLUMN comment_count INTEGER NOT NULL DEFAULT 0",
            "share_count": "ALTER TABLE feedback ADD COLUMN share_count INTEGER NOT NULL DEFAULT 0",
            "engagement_rate": "ALTER TABLE feedback ADD COLUMN engagement_rate FLOAT NOT NULL DEFAULT 0",
            "trending_score": "ALTER TABLE feedback ADD COLUMN trending_score FLOAT NOT NULL DEFAULT 0",
            "feedback_summary": "ALTER TABLE feedback ADD COLUMN feedback_summary TEXT",
            "updated_at": "ALTER TABLE feedback ADD COLUMN updated_at DATETIME",
        },
    )


def _ensure_message_columns() -> None:
    _ensure_columns(
        "messages",
        {
            "type": "ALTER TABLE messages ADD COLUMN type VARCHAR(20) NOT NULL DEFAULT 'system'",
            "is_read": "ALTER TABLE messages ADD COLUMN is_read BOOLEAN NOT NULL DEFAULT 0",
            "related_id": "ALTER TABLE messages ADD COLUMN related_id INTEGER",
            "related_type": "ALTER TABLE messages ADD COLUMN related_type VARCHAR(20)",
            "recipient_id": "ALTER TABLE messages ADD COLUMN recipient_id INTEGER",
            "read_at": "ALTER TABLE messages ADD COLUMN read_at DATETIME",
        },
    )


def _backfill_message_recipients() -> None:
    """尽量为历史消息补齐 recipient_id，避免消息中心串号。"""
    inspector = inspect(engine)
    if "messages" not in inspector.get_table_names():
        return

    message_columns = {column["name"] for column in inspector.get_columns("messages")}
    if "recipient_id" not in message_columns:
        return

    from app.models.article import Article
    from app.models.message import Message
    from app.models.user import User

    db = SessionLocal()
    try:
        pending_messages = db.query(Message).filter(Message.recipient_id.is_(None)).all()
        if not pending_messages:
            return

        article_ids = [msg.related_id for msg in pending_messages if msg.related_type == "article" and msg.related_id]
        message_ids = [msg.related_id for msg in pending_messages if msg.related_type == "message" and msg.related_id]

        article_author_map = {
            article.id: article.author_id
            for article in db.query(Article).filter(Article.id.in_(article_ids)).all()
            if article.author_id
        } if article_ids else {}

        related_message_map = {
            item.id: item
            for item in db.query(Message).filter(Message.id.in_(message_ids)).all()
        } if message_ids else {}

        user_name_map: dict[str, int] = {}
        for user in db.query(User).all():
            for name in (user.username, user.nickname, user.full_name):
                normalized = (name or "").strip()
                if normalized and normalized not in user_name_map:
                    user_name_map[normalized] = user.id

        updated = 0
        for msg in pending_messages:
            inferred_recipient_id = None

            if msg.related_type == "article" and msg.related_id:
                inferred_recipient_id = article_author_map.get(msg.related_id)

            if inferred_recipient_id is None and msg.related_type == "message" and msg.related_id:
                original = related_message_map.get(msg.related_id)
                if original and original.recipient_id:
                    inferred_recipient_id = original.recipient_id

            if inferred_recipient_id is None:
                sender = (msg.sender or "").strip()
                if sender and sender.lower() != "system":
                    inferred_recipient_id = user_name_map.get(sender)

            if inferred_recipient_id:
                msg.recipient_id = inferred_recipient_id
                updated += 1

        if updated:
            db.commit()
            get_logger(__name__).info("Backfilled recipient_id for %s historical messages", updated)
        else:
            db.rollback()
    except Exception as exc:
        db.rollback()
        get_logger(__name__).warning("Message recipient backfill skipped: %s", exc)
    finally:
        db.close()


def ensure_schema_migrations() -> None:
    """确保所有模型表已创建"""
    try:
        Base.metadata.create_all(bind=engine)
        _ensure_clue_columns()
        _ensure_topic_columns()
        _ensure_article_columns()
        _ensure_feedback_columns()
        _ensure_message_columns()
        _backfill_message_recipients()
        get_logger(__name__).info("Schema migrations applied successfully")
    except Exception as exc:
        get_logger(__name__).warning("Schema migration skipped: %s", exc)
