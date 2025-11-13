"""Unit tests for conversation logging and caching tools."""

import json
from datetime import datetime, timedelta, timezone

import pytest

from mcp_server.tools.conversation import ConversationTools


class TestConversationTools:
    """Test suite for ConversationTools."""

    @pytest.fixture
    def conversation_tools(self):
        """Create a ConversationTools instance for testing."""
        return ConversationTools()

    # ========================================
    # Conversation Logging Tests
    # ========================================

    def test_conversation_tools_initialization(self, conversation_tools):
        """Test ConversationTools initializes with empty logs.

        Arrange: Create ConversationTools instance
        Act: Check initial state
        Assert: Logs and cache are empty
        """
        assert conversation_tools.conversation_log == []
        assert conversation_tools.weather_cache == {}

    def test_log_message_basic(self, conversation_tools):
        """Test basic message logging.

        Arrange: Create conversation tools
        Act: Log a message
        Assert: Message appears in log with timestamp
        """
        conversation_tools.log_message("user", "Hello")

        assert len(conversation_tools.conversation_log) == 1
        entry = conversation_tools.conversation_log[0]
        assert entry["role"] == "user"
        assert entry["content"] == "Hello"
        assert "timestamp" in entry
        # Verify timestamp is valid ISO format
        datetime.fromisoformat(entry["timestamp"])

    def test_log_multiple_messages(self, conversation_tools):
        """Test logging multiple messages in sequence.

        Arrange: Create conversation tools
        Act: Log multiple messages with different roles
        Assert: All messages logged in order
        """
        conversation_tools.log_message("user", "What's the weather?")
        conversation_tools.log_message("assistant", "Let me check that.")
        conversation_tools.log_message("system", "Fetched forecast data")

        assert len(conversation_tools.conversation_log) == 3
        assert conversation_tools.conversation_log[0]["role"] == "user"
        assert conversation_tools.conversation_log[1]["role"] == "assistant"
        assert conversation_tools.conversation_log[2]["role"] == "system"

    def test_get_conversation_log_empty(self, conversation_tools):
        """Test getting conversation log when empty.

        Arrange: Create conversation tools with no messages
        Act: Get conversation log
        Assert: Returns empty JSON array
        """
        result = conversation_tools.get_conversation_log()
        parsed = json.loads(result)

        assert parsed == []

    def test_get_conversation_log_with_messages(self, conversation_tools):
        """Test getting conversation log with messages.

        Arrange: Log several messages
        Act: Get full conversation log
        Assert: Returns all messages as JSON
        """
        conversation_tools.log_message("user", "Message 1")
        conversation_tools.log_message("assistant", "Message 2")

        result = conversation_tools.get_conversation_log()
        parsed = json.loads(result)

        assert len(parsed) == 2
        assert parsed[0]["content"] == "Message 1"
        assert parsed[1]["content"] == "Message 2"

    def test_get_conversation_log_with_limit(self, conversation_tools):
        """Test getting limited number of recent messages.

        Arrange: Log 5 messages
        Act: Get last 2 messages
        Assert: Returns only the 2 most recent
        """
        for i in range(5):
            conversation_tools.log_message("user", f"Message {i}")

        result = conversation_tools.get_conversation_log(limit=2)
        parsed = json.loads(result)

        assert len(parsed) == 2
        assert parsed[0]["content"] == "Message 3"
        assert parsed[1]["content"] == "Message 4"

    def test_get_conversation_log_limit_exceeds_size(self, conversation_tools):
        """Test getting conversation log when limit exceeds size.

        Arrange: Log 2 messages
        Act: Request limit of 10
        Assert: Returns all 2 messages
        """
        conversation_tools.log_message("user", "Message 1")
        conversation_tools.log_message("user", "Message 2")

        result = conversation_tools.get_conversation_log(limit=10)
        parsed = json.loads(result)

        assert len(parsed) == 2

    # ========================================
    # Weather Caching Tests
    # ========================================

    def test_cache_weather_data(self, conversation_tools):
        """Test caching weather data.

        Arrange: Create conversation tools
        Act: Cache weather data
        Assert: Data stored with timestamp and type
        """
        conversation_tools.cache_weather_data("alerts_CA", "Fire warning active", "alerts")

        assert "alerts_CA" in conversation_tools.weather_cache
        cached = conversation_tools.weather_cache["alerts_CA"]
        assert cached["data"] == "Fire warning active"
        assert cached["type"] == "alerts"
        assert isinstance(cached["timestamp"], datetime)

    def test_cache_multiple_items(self, conversation_tools):
        """Test caching multiple weather items.

        Arrange: Create conversation tools
        Act: Cache multiple different items
        Assert: All items stored separately
        """
        conversation_tools.cache_weather_data("alerts_CA", "CA alerts", "alerts")
        conversation_tools.cache_weather_data("alerts_NY", "NY alerts", "alerts")
        conversation_tools.cache_weather_data("forecast_37.77_-122.41", "SF forecast", "forecast")

        assert len(conversation_tools.weather_cache) == 3
        assert "alerts_CA" in conversation_tools.weather_cache
        assert "alerts_NY" in conversation_tools.weather_cache
        assert "forecast_37.77_-122.41" in conversation_tools.weather_cache

    def test_get_cached_weather_found_fresh(self, conversation_tools):
        """Test getting cached weather data that is still fresh.

        Arrange: Cache weather data
        Act: Retrieve within expiry time
        Assert: Returns cached data
        """
        conversation_tools.cache_weather_data("alerts_CA", "Fresh data", "alerts")

        result = conversation_tools.get_cached_weather("alerts_CA", max_age_minutes=60)

        assert result == "Fresh data"

    def test_get_cached_weather_not_found(self, conversation_tools):
        """Test getting cached weather data that doesn't exist.

        Arrange: Create conversation tools with empty cache
        Act: Try to retrieve non-existent data
        Assert: Returns None
        """
        result = conversation_tools.get_cached_weather("alerts_CA", max_age_minutes=60)

        assert result is None

    def test_get_cached_weather_expired(self, conversation_tools):
        """Test getting cached weather data that has expired.

        Arrange: Cache weather data with old timestamp
        Act: Retrieve with short expiry time
        Assert: Returns None and removes from cache
        """
        # Manually insert old data
        old_timestamp = datetime.now(tz=timezone.utc) - timedelta(minutes=90)
        conversation_tools.weather_cache["alerts_CA"] = {
            "timestamp": old_timestamp,
            "data": "Old data",
            "type": "alerts",
        }

        result = conversation_tools.get_cached_weather("alerts_CA", max_age_minutes=60)

        assert result is None
        assert "alerts_CA" not in conversation_tools.weather_cache

    def test_cache_update_overwrites(self, conversation_tools):
        """Test caching same key overwrites previous data.

        Arrange: Cache initial data
        Act: Cache new data with same key
        Assert: New data replaces old data
        """
        conversation_tools.cache_weather_data("alerts_CA", "Old data", "alerts")
        conversation_tools.cache_weather_data("alerts_CA", "New data", "alerts")

        result = conversation_tools.get_cached_weather("alerts_CA")

        assert result == "New data"

    def test_get_all_cached_weather_empty(self, conversation_tools):
        """Test getting all cached weather when cache is empty.

        Arrange: Create conversation tools with empty cache
        Act: Get all cached weather
        Assert: Returns empty JSON array
        """
        result = conversation_tools.get_all_cached_weather()
        parsed = json.loads(result)

        assert parsed == []

    def test_get_all_cached_weather_with_data(self, conversation_tools):
        """Test getting all cached weather with multiple items.

        Arrange: Cache multiple weather items
        Act: Get all cached weather
        Assert: Returns summary with keys, types, timestamps, ages
        """
        conversation_tools.cache_weather_data("alerts_CA", "A" * 250, "alerts")
        conversation_tools.cache_weather_data("forecast_40.0_-74.0", "Forecast", "forecast")

        result = conversation_tools.get_all_cached_weather()
        parsed = json.loads(result)

        assert len(parsed) == 2
        assert any(item["key"] == "alerts_CA" for item in parsed)
        assert any(item["key"] == "forecast_40.0_-74.0" for item in parsed)

        # Check structure of first item
        first_item = parsed[0]
        assert "key" in first_item
        assert "type" in first_item
        assert "timestamp" in first_item
        assert "age_minutes" in first_item
        assert "data_preview" in first_item

    def test_get_all_cached_weather_truncates_preview(self, conversation_tools):
        """Test that data preview is truncated for long data.

        Arrange: Cache very long weather data
        Act: Get all cached weather
        Assert: Preview is truncated with ellipsis
        """
        long_data = "A" * 300
        conversation_tools.cache_weather_data("alerts_CA", long_data, "alerts")

        result = conversation_tools.get_all_cached_weather()
        parsed = json.loads(result)

        preview = parsed[0]["data_preview"]
        assert len(preview) <= 203  # 200 chars + "..."
        assert preview.endswith("...")

    def test_get_all_cached_weather_no_truncate_short(self, conversation_tools):
        """Test that short data is not truncated.

        Arrange: Cache short weather data
        Act: Get all cached weather
        Assert: Full data shown without ellipsis
        """
        short_data = "Short forecast"
        conversation_tools.cache_weather_data("forecast_40.0_-74.0", short_data, "forecast")

        result = conversation_tools.get_all_cached_weather()
        parsed = json.loads(result)

        preview = parsed[0]["data_preview"]
        assert preview == short_data
        assert not preview.endswith("...")

    def test_clear_expired_cache_empty(self, conversation_tools):
        """Test clearing expired cache when cache is empty.

        Arrange: Create conversation tools with empty cache
        Act: Clear expired cache
        Assert: Returns 0 entries removed
        """
        removed = conversation_tools.clear_expired_cache(max_age_minutes=60)

        assert removed == 0

    def test_clear_expired_cache_no_expired(self, conversation_tools):
        """Test clearing expired cache when nothing is expired.

        Arrange: Cache fresh data
        Act: Clear expired cache
        Assert: No entries removed, cache unchanged
        """
        conversation_tools.cache_weather_data("alerts_CA", "Fresh", "alerts")

        removed = conversation_tools.clear_expired_cache(max_age_minutes=60)

        assert removed == 0
        assert "alerts_CA" in conversation_tools.weather_cache

    def test_clear_expired_cache_all_expired(self, conversation_tools):
        """Test clearing expired cache when all entries are expired.

        Arrange: Cache old data
        Act: Clear expired cache
        Assert: All entries removed
        """
        old_timestamp = datetime.now(tz=timezone.utc) - timedelta(minutes=90)
        conversation_tools.weather_cache["alerts_CA"] = {
            "timestamp": old_timestamp,
            "data": "Old",
            "type": "alerts",
        }
        conversation_tools.weather_cache["alerts_NY"] = {
            "timestamp": old_timestamp,
            "data": "Old",
            "type": "alerts",
        }

        removed = conversation_tools.clear_expired_cache(max_age_minutes=60)

        assert removed == 2
        assert len(conversation_tools.weather_cache) == 0

    def test_clear_expired_cache_mixed(self, conversation_tools):
        """Test clearing expired cache with mix of fresh and old data.

        Arrange: Cache mix of fresh and old data
        Act: Clear expired cache
        Assert: Only old entries removed
        """
        # Fresh data
        conversation_tools.cache_weather_data("alerts_CA", "Fresh", "alerts")

        # Old data
        old_timestamp = datetime.now(tz=timezone.utc) - timedelta(minutes=90)
        conversation_tools.weather_cache["alerts_NY"] = {
            "timestamp": old_timestamp,
            "data": "Old",
            "type": "alerts",
        }

        removed = conversation_tools.clear_expired_cache(max_age_minutes=60)

        assert removed == 1
        assert "alerts_CA" in conversation_tools.weather_cache
        assert "alerts_NY" not in conversation_tools.weather_cache

    def test_clear_expired_cache_custom_age(self, conversation_tools):
        """Test clearing expired cache with custom max age.

        Arrange: Cache data 45 minutes old
        Act: Clear with 30 minute expiry
        Assert: Entry removed
        """
        old_timestamp = datetime.now(tz=timezone.utc) - timedelta(minutes=45)
        conversation_tools.weather_cache["alerts_CA"] = {
            "timestamp": old_timestamp,
            "data": "Data",
            "type": "alerts",
        }

        removed = conversation_tools.clear_expired_cache(max_age_minutes=30)

        assert removed == 1
        assert len(conversation_tools.weather_cache) == 0

    # ========================================
    # Integration Tests
    # ========================================

    def test_full_workflow_with_caching(self, conversation_tools):
        """Test complete workflow: log, cache, retrieve, check cache.

        Arrange: Create conversation tools
        Act: Log messages, cache data, retrieve, check all cached
        Assert: All operations work together correctly
        """
        # Log some activity
        conversation_tools.log_message("system", "Fetching CA alerts")
        conversation_tools.log_message("system", "Caching CA alerts")

        # Cache weather data
        conversation_tools.cache_weather_data("alerts_CA", "Fire warning", "alerts")

        # Verify we can get cached data
        cached = conversation_tools.get_cached_weather("alerts_CA")
        assert cached == "Fire warning"

        # Check conversation log
        log = conversation_tools.get_conversation_log()
        parsed = json.loads(log)
        assert len(parsed) == 2

        # Check all cached items
        all_cached = conversation_tools.get_all_cached_weather()
        parsed_cache = json.loads(all_cached)
        assert len(parsed_cache) == 1
        assert parsed_cache[0]["key"] == "alerts_CA"

    def test_cache_behavior_across_time(self, conversation_tools):
        """Test cache behavior simulating passage of time.

        Arrange: Cache data
        Act: Check immediately, simulate expiry, check again
        Assert: Fresh returns data, expired returns None
        """
        # Cache data
        conversation_tools.cache_weather_data("alerts_CA", "Data", "alerts")

        # Should be fresh immediately
        result1 = conversation_tools.get_cached_weather("alerts_CA", max_age_minutes=60)
        assert result1 == "Data"

        # Simulate old data by manipulating timestamp
        old_timestamp = datetime.now(tz=timezone.utc) - timedelta(minutes=90)
        conversation_tools.weather_cache["alerts_CA"]["timestamp"] = old_timestamp

        # Should now be expired
        result2 = conversation_tools.get_cached_weather("alerts_CA", max_age_minutes=60)
        assert result2 is None
        assert "alerts_CA" not in conversation_tools.weather_cache
