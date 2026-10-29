"""MongoDB Atlas storage for chat logs and feedback.

Every function returns True/False instead of raising, so the website keeps
working when MongoDB is unreachable. After a failure we skip MongoDB for a
short cool-down period so visitors are not slowed down by repeated timeouts.
"""
import logging
import time
from datetime import datetime, timezone

from django.conf import settings
from pymongo import MongoClient
from pymongo.errors import PyMongoError

logger = logging.getLogger("gather.mongo")

_client = None
_down_until = 0.0
COOLDOWN_SECONDS = 60


def get_db():
    global _client
    if not settings.MONGODB_URI:
        return None
    if time.monotonic() < _down_until:
        return None
    if _client is None:
        _client = MongoClient(
            settings.MONGODB_URI,
            serverSelectionTimeoutMS=settings.MONGODB_TIMEOUT_MS,
            connectTimeoutMS=settings.MONGODB_TIMEOUT_MS,
            socketTimeoutMS=settings.MONGODB_TIMEOUT_MS * 2,
            appname="gather-co",
        )
    return _client[settings.MONGODB_DATABASE]


def _mark_down(action, exc):
    global _down_until
    _down_until = time.monotonic() + COOLDOWN_SECONDS
    # Log the exception type only: messages can contain the connection host.
    logger.warning("MongoDB unavailable during %s (%s); chat logging paused for %ss",
                   action, type(exc).__name__, COOLDOWN_SECONDS)


def reset_state():
    """Used by tests to clear the cached client and cool-down."""
    global _client, _down_until
    _client = None
    _down_until = 0.0


def _insert(collection, document):
    try:
        db = get_db()
        if db is None:
            return False
        document["timestamp"] = datetime.now(timezone.utc)
        db[collection].insert_one(document)
        return True
    except PyMongoError as exc:
        _mark_down(f"insert into {collection}", exc)
        return False


def log_chat(conversation_id, message_id, question, answer, faq_ids, error_codes, ticket_created, source):
    return _insert("chat_logs", {
        "conversation_id": conversation_id,
        "message_id": message_id,
        "question": question,
        "answer": answer,
        "faq_ids": faq_ids,
        "error_codes": error_codes,
        "ticket_created": ticket_created,
        "source": source,
    })


def save_feedback(conversation_id, message_id, rating, comment):
    return _insert("feedback", {
        "conversation_id": conversation_id,
        "message_id": message_id,
        "rating": rating,
        "comment": comment,
    })


def ping():
    """Returns True/False when configured, or None when MongoDB is not configured."""
    if not settings.MONGODB_URI:
        return None
    try:
        db = get_db()
        if db is None:
            return False
        db.command("ping")
        return True
    except PyMongoError as exc:
        _mark_down("health ping", exc)
        return False
