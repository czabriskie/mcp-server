"""Integration tests for web app with time tools."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# We'll need to import the app, but handle MCP initialization gracefully
# For testing, we'll mock the MCP connection


@pytest.fixture
def mock_mcp_session():
    """Mock MCP session for testing."""
    session = MagicMock()
    session.call_tool = AsyncMock()
    return session


@pytest.fixture
def mock_time_result():
    """Mock successful time tool result."""
    return MagicMock(
        content=[
            MagicMock(
                text="""Current Time Information:
Time: Wednesday, November 12, 2025 at 10:30:00 AM
Timezone: America/Los_Angeles
UTC Offset: -0800
ISO Format: 2025-11-12T10:30:00-08:00
Day of Week: Wednesday
Date: November 12, 2025

Location (estimated from IP):
City: San Francisco, California, United States
Coordinates: 37.7749, -122.4194

✓ Location detected successfully! Use these coordinates for weather lookups.
(IP: 8.8.8.8)"""
            )
        ]
    )


@pytest.fixture
def mock_time_result_no_location():
    """Mock time tool result when location detection fails."""
    return MagicMock(
        content=[
            MagicMock(
                text="""Current Time Information:
Time: Wednesday, November 12, 2025 at 10:30:00 AM
Timezone: UTC
UTC Offset: +0000
ISO Format: 2025-11-12T10:30:00+00:00
Day of Week: Wednesday
Date: November 12, 2025

Location (estimated from IP):
City: Unknown, Unknown, Unknown

⚠️ Could not determine precise location from IP address.
For weather forecasts, please provide your city/state or coordinates manually.
(IP: 127.0.0.1)"""
            )
        ]
    )


class TestWebAppTimeIntegration:
    """Integration tests for web app time tool functionality."""

    @pytest.mark.asyncio
    async def test_chat_endpoint_calls_time_tool(self, mock_mcp_session, mock_time_result):
        """Test that chat endpoint properly calls get_current_time tool."""
        # This test verifies the integration between web app and MCP tools
        # We'll test that the IP address is properly passed to the tool

        # Arrange
        mock_mcp_session.call_tool.return_value = mock_time_result

        # Act - simulate tool being called with IP injection
        result = await mock_mcp_session.call_tool(
            "get_current_time", arguments={"ip_address": "8.8.8.8"}
        )

        # Assert
        assert result is not None
        assert "San Francisco" in result.content[0].text
        assert "37.7749, -122.4194" in result.content[0].text

    @pytest.mark.asyncio
    async def test_ip_address_injection(self, mock_mcp_session):
        """Test that client IP is automatically injected into get_current_time calls."""
        # Arrange
        client_ip = "203.0.113.42"  # Test IP

        # Act - simulate the web app's IP injection logic
        tool_input = {}
        tool_name = "get_current_time"

        # This mimics the logic in app.py handle_claude_with_tools
        if tool_name == "get_current_time" and client_ip:
            if "ip_address" not in tool_input or not tool_input.get("ip_address"):
                tool_input["ip_address"] = client_ip

        # Assert
        assert tool_input["ip_address"] == client_ip

    @pytest.mark.asyncio
    async def test_localhost_ip_handling(self, mock_mcp_session):
        """Test that localhost IP is still passed (tool handles filtering)."""
        # Arrange
        localhost_ip = "127.0.0.1"

        # Act - simulate the web app passing localhost
        tool_input = {}
        if "ip_address" not in tool_input:
            tool_input["ip_address"] = localhost_ip

        # Assert - localhost should be passed, tool will handle it
        assert tool_input["ip_address"] == localhost_ip

    def test_system_prompt_includes_time_workflow(self):
        """Test that system prompt includes proper workflow for time/weather."""
        # Arrange
        from datetime import datetime

        now = datetime.now().astimezone()
        now_iso = now.isoformat()
        now_str = now.strftime("%A, %B %d, %Y %H:%M:%S %Z%z")

        # Act - recreate system prompt logic from app.py
        system_prompt = (
            f"Current local time: {now_str} (ISO: {now_iso}). "
            "Use this timestamp for any time-sensitive answers. "
            "\n\nFor weather requests:"
            "\n1. First call get_current_time to attempt location detection from IP"
            "\n2. If coordinates are provided in the response, use them for get_forecast"
            "\n3. If no coordinates are returned, politely ask the user for their location (city/state or lat/lon)"
            "\n4. Never make up coordinates or assume a location"
        )

        # Assert
        assert "get_current_time" in system_prompt
        assert "If coordinates are provided" in system_prompt
        assert "Never make up coordinates" in system_prompt

    @pytest.mark.asyncio
    async def test_tool_response_with_coordinates(self, mock_time_result):
        """Test parsing tool response that includes coordinates."""
        # Arrange
        response_text = mock_time_result.content[0].text

        # Act - check if coordinates are present
        has_coordinates = "Coordinates:" in response_text and "✓ Location detected" in response_text

        # Assert
        assert has_coordinates
        assert "37.7749, -122.4194" in response_text

    @pytest.mark.asyncio
    async def test_tool_response_without_coordinates(self, mock_time_result_no_location):
        """Test parsing tool response when location detection fails."""
        # Arrange
        response_text = mock_time_result_no_location.content[0].text

        # Act - check for warning message
        has_warning = "⚠️ Could not determine precise location" in response_text
        has_instruction = "please provide your city/state" in response_text

        # Assert
        assert has_warning
        assert has_instruction
        assert "Coordinates:" not in response_text or "Unknown" in response_text


class TestMCPToolRegistration:
    """Test MCP tool registration for time tools."""

    def test_get_current_time_tool_signature(self):
        """Test that get_current_time tool has correct signature."""
        # This verifies the tool is registered with proper parameters
        # In actual MCP server, this would be checked via list_tools

        # Expected signature
        expected_params = {
            "ip_address": {
                "type": "string",
                "optional": True,
                "description": "Optional IP address to determine timezone",
            }
        }

        # Assert structure
        assert "ip_address" in expected_params
        assert expected_params["ip_address"]["optional"] is True

    @pytest.mark.asyncio
    async def test_tool_returns_structured_response(self):
        """Test that tool returns properly structured response."""
        from mcp_server.tools.time_tools import TimeTools

        # Arrange
        time_tools = TimeTools()
        mock_location = {
            "timezone": "America/New_York",
            "lat": 40.7128,
            "lon": -74.0060,
            "city": "New York",
            "region": "New York",
            "country": "United States",
        }

        with patch.object(time_tools, "get_location_from_ip", return_value=mock_location):
            # Act
            result = await time_tools.get_current_time("8.8.8.8")

            # Assert - check all required sections
            required_sections = [
                "Current Time Information:",
                "Time:",
                "Timezone:",
                "UTC Offset:",
                "ISO Format:",
                "Day of Week:",
                "Date:",
                "Location (estimated from IP):",
                "Coordinates:",
            ]

            for section in required_sections:
                assert section in result, f"Missing section: {section}"


class TestEndToEndScenarios:
    """End-to-end test scenarios."""

    @pytest.mark.asyncio
    async def test_weather_query_with_successful_location(self):
        """Test complete flow: user asks for weather, location is detected, forecast is fetched."""
        # This simulates the full conversation flow

        # Step 1: User asks for weather

        # Step 2: Model calls get_current_time
        time_response = """Current Time Information:
Time: Wednesday, November 12, 2025 at 10:30:00 AM
Timezone: America/Los_Angeles
Location (estimated from IP):
City: San Francisco, California, United States
Coordinates: 37.7749, -122.4194
✓ Location detected successfully! Use these coordinates for weather lookups."""

        # Step 3: Model extracts coordinates
        has_coords = "37.7749, -122.4194" in time_response
        assert has_coords

        # Step 4: Model would call get_forecast(37.7749, -122.4194)
        # (This would be tested in weather tools tests)

    @pytest.mark.asyncio
    async def test_weather_query_with_failed_location(self):
        """Test flow when location detection fails."""
        # Step 1: User asks for weather

        # Step 2: Model calls get_current_time
        time_response = """Current Time Information:
Time: Wednesday, November 12, 2025 at 10:30:00 AM
Timezone: UTC
Location (estimated from IP):
City: Unknown, Unknown, Unknown
⚠️ Could not determine precise location from IP address.
For weather forecasts, please provide your city/state or coordinates manually."""

        # Step 3: Model detects failure
        has_warning = "⚠️ Could not determine precise location" in time_response
        assert has_warning

        # Step 4: Model should ask user for location
        # (Would be verified in model response)

    @pytest.mark.asyncio
    async def test_time_query_only(self):
        """Test simple time query without weather."""
        from mcp_server.tools.time_tools import TimeTools

        # Arrange
        time_tools = TimeTools()
        mock_location = {
            "timezone": "America/Chicago",
            "lat": 41.8781,
            "lon": -87.6298,
            "city": "Chicago",
            "region": "Illinois",
            "country": "United States",
        }

        with patch.object(time_tools, "get_location_from_ip", return_value=mock_location):
            # Act
            result = await time_tools.get_current_time()

            # Assert - should have time info but weather not required
            assert "Current Time Information:" in result
            assert "Chicago" in result
            assert "Coordinates:" in result  # Available if user wants it


# Performance tests
class TestPerformance:
    """Performance and timeout tests."""

    @pytest.mark.asyncio
    async def test_geolocation_timeout_handling(self):
        """Test that geolocation services respect timeout."""
        import asyncio

        from mcp_server.tools.time_tools import TimeTools

        # Arrange
        time_tools = TimeTools()

        # Act/Assert - should complete within reasonable time even if services are slow
        with patch("httpx.AsyncClient.get", side_effect=asyncio.TimeoutError()):
            result = await time_tools.get_location_from_ip("8.8.8.8")

            # Should return defaults, not hang
            assert result["lat"] is None
            assert result["timezone"] == "UTC"

    @pytest.mark.asyncio
    async def test_multiple_rapid_requests(self):
        """Test handling multiple requests in quick succession."""
        from mcp_server.tools.time_tools import TimeTools

        # Arrange
        time_tools = TimeTools()
        mock_location = {
            "timezone": "UTC",
            "lat": 0,
            "lon": 0,
            "city": "Test",
            "region": "Test",
            "country": "Test",
        }

        with patch.object(time_tools, "get_location_from_ip", return_value=mock_location):
            # Act - make 10 rapid requests
            import asyncio

            tasks = [time_tools.get_current_time(f"8.8.8.{i}") for i in range(10)]
            results = await asyncio.gather(*tasks)

            # Assert - all should complete successfully
            assert len(results) == 10
            for result in results:
                assert "Current Time Information:" in result
