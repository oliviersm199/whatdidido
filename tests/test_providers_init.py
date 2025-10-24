"""Tests for providers/__init__.py helper functions."""

import pytest

from providers import get_provider


class TestGetProvider:
    """Tests for get_provider function."""

    def test_get_provider_jira(self):
        """Test getting Jira provider by name."""
        provider = get_provider("Jira")
        assert provider.get_name() == "Jira"

    def test_get_provider_linear(self):
        """Test getting Linear provider by name."""
        provider = get_provider("Linear")
        assert provider.get_name() == "Linear"

    def test_get_provider_case_insensitive(self):
        """Test that provider lookup is case-insensitive."""
        provider = get_provider("jira")
        assert provider.get_name() == "Jira"

        provider = get_provider("LINEAR")
        assert provider.get_name() == "Linear"

    def test_get_provider_not_found(self):
        """Test that ValueError is raised for unknown provider."""
        with pytest.raises(ValueError, match="Provider with name 'Unknown' not found"):
            get_provider("Unknown")
