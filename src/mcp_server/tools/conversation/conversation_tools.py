"""Conversation logging and weather caching tools."""

import json
from datetime import datetime, timedelta, timezone
from typing import Any

# Constants
PREVIEW_LENGTH = 200


class ConversationTools:
    """Tools for logging conversations and caching weather data."""

    def __init__(self) -> None:
        """Initialize conversation tools with in-memory storage."""
        self.conversation_log: list[dict[str, Any]] = []
        self.weather_cache: dict[str, dict[str, Any]] = {}

    def log_message(self, role: str, content: str) -> None:
        """Log a conversation message.

        Args:
            role: Message role (user, assistant, system)
            content: Message content
        """
        entry = {
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "role": role,
            "content": content,
        }
        self.conversation_log.append(entry)

    def get_conversation_log(self, limit: int | None = None) -> str:
        """Get the conversation log.

        Args:
            limit: Maximum number of messages to return (None = all)

        Returns:
            JSON formatted conversation log
        """
        messages = self.conversation_log[-limit:] if limit else self.conversation_log
        return json.dumps(messages, indent=2)

    def cache_weather_data(self, cache_key: str, data: str, cache_type: str) -> None:
        """Cache weather data with timestamp.

        Args:
            cache_key: Unique identifier (e.g., "alerts_CA" or "forecast_37.77_-122.41")
            data: Weather data to cache
            cache_type: Type of data ("alerts" or "forecast")
        """
        self.weather_cache[cache_key] = {
            "timestamp": datetime.now(tz=timezone.utc),
            "data": data,
            "type": cache_type,
        }

    def get_cached_weather(self, cache_key: str, max_age_minutes: int = 60) -> str | None:
        """Get cached weather data if still fresh.

        Args:
            cache_key: Cache identifier to lookup
            max_age_minutes: Maximum age in minutes before cache expires

        Returns:
            Cached data if fresh, None if expired or not found
        """
        if cache_key not in self.weather_cache:
            return None

        cached = self.weather_cache[cache_key]
        age = datetime.now(tz=timezone.utc) - cached["timestamp"]

        if age <= timedelta(minutes=max_age_minutes):
            cached_data: str = cached["data"]
            return cached_data

        # Cache expired, remove it
        del self.weather_cache[cache_key]
        return None

    def get_all_cached_weather(self) -> str:
        """Get all cached weather data with timestamps.

        Returns:
            JSON formatted cache contents
        """
        cache_summary = []
        for key, value in self.weather_cache.items():
            age = datetime.now(tz=timezone.utc) - value["timestamp"]
            cache_summary.append(
                {
                    "key": key,
                    "type": value["type"],
                    "timestamp": value["timestamp"].isoformat(),
                    "age_minutes": int(age.total_seconds() / 60),
                    "data_preview": value["data"][:PREVIEW_LENGTH] + "..."
                    if len(value["data"]) > PREVIEW_LENGTH
                    else value["data"],
                }
            )
        return json.dumps(cache_summary, indent=2)

    def clear_expired_cache(self, max_age_minutes: int = 60) -> int:
        """Clear expired cache entries.

        Args:
            max_age_minutes: Maximum age before considering expired

        Returns:
            Number of entries removed
        """
        now = datetime.now(tz=timezone.utc)
        expired_keys = [
            key
            for key, value in self.weather_cache.items()
            if now - value["timestamp"] > timedelta(minutes=max_age_minutes)
        ]

        for key in expired_keys:
            del self.weather_cache[key]

        return len(expired_keys)
