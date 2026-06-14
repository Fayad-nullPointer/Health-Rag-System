"""
Redis-backed per-user chat memory.

Stores recent conversation turns in a Redis list so the RAG pipeline
can inject conversational context into prompts.  All operations degrade
gracefully – if Redis is unavailable the chatbot simply has no memory.
"""

import json
import logging

from cache_layer import CacheLayer
from config import CACHE_TTL_MEMORY, MAX_MEMORY_MESSAGES

logger = logging.getLogger(__name__)


class ChatMemory:
    """Per-user conversation memory backed by Redis lists.

    Args:
        cache: A ``CacheLayer`` instance (provides the Redis connection).
        max_messages: Maximum number of *pairs* (user + assistant) to keep.
    """

    KEY_PREFIX = "memory"

    def __init__(
        self, cache: CacheLayer, max_messages: int = MAX_MEMORY_MESSAGES
    ) -> None:
        self._cache = cache
        self._max_messages = max_messages
        # Each pair = 2 entries, so cap the list at max_messages * 2
        self._max_entries = max_messages * 2

    # ── helpers ────────────────────────────────────────────────────────────

    def _key(self, user_id: str) -> str:
        """Build the Redis key for a given user."""
        return f"{self.KEY_PREFIX}:{user_id}"

    # ── public API ─────────────────────────────────────────────────────────

    def add_message(self, user_id: str, role: str, content: str) -> None:
        """Append a message to the user's conversation history.

        The list is capped at ``max_messages * 2`` entries and the TTL is
        refreshed on every write so idle conversations expire.
        """
        if not self._cache.is_available:
            return
        try:
            r = self._cache._redis
            key = self._key(user_id)
            payload = json.dumps({"role": role, "content": content}, ensure_ascii=False)
            r.rpush(key, payload)
            r.ltrim(key, -self._max_entries, -1)
            r.expire(key, CACHE_TTL_MEMORY)
        except Exception as exc:
            logger.debug("ChatMemory.add_message error for %s: %s", user_id, exc)

    def get_history(self, user_id: str) -> list[dict]:
        """Return the full conversation history as a list of dicts.

        Returns an empty list if Redis is unavailable or the key does not exist.
        """
        if not self._cache.is_available:
            return []
        try:
            r = self._cache._redis
            raw_items = r.lrange(self._key(user_id), 0, -1)
            return [json.loads(item) for item in raw_items]
        except Exception as exc:
            logger.debug("ChatMemory.get_history error for %s: %s", user_id, exc)
            return []

    def clear(self, user_id: str) -> None:
        """Delete the entire conversation history for a user."""
        if not self._cache.is_available:
            return
        try:
            self._cache._redis.delete(self._key(user_id))
        except Exception as exc:
            logger.debug("ChatMemory.clear error for %s: %s", user_id, exc)

    def format_for_prompt(self, user_id: str) -> str:
        """Format conversation history as a human-readable string.

        Example output::

            User: I feel sad
            Assistant: I'm sorry to hear that...
            User: What can I do?

        Returns an empty string if there is no history.
        """
        history = self.get_history(user_id)
        if not history:
            return ""

        lines: list[str] = []
        for entry in history:
            role_label = "User" if entry["role"] == "user" else "Assistant"
            lines.append(f"{role_label}: {entry['content']}")
        return "\n".join(lines)
