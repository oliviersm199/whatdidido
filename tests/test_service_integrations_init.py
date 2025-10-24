"""Tests for service_integrations/__init__.py helper functions."""

import pytest

from service_integrations import get_service_integration


class TestGetServiceIntegration:
    """Tests for get_service_integration function."""

    def test_get_service_integration_openai(self):
        """Test getting OpenAI service integration by name."""
        service = get_service_integration("OpenAI")
        assert service.get_name() == "OpenAI"

    def test_get_service_integration_case_insensitive(self):
        """Test that service integration lookup is case-insensitive."""
        service = get_service_integration("openai")
        assert service.get_name() == "OpenAI"

        service = get_service_integration("OPENAI")
        assert service.get_name() == "OpenAI"

    def test_get_service_integration_not_found(self):
        """Test that ValueError is raised for unknown service integration."""
        with pytest.raises(
            ValueError, match="Service integration with name 'Unknown' not found"
        ):
            get_service_integration("Unknown")
