"""
Tests for the OpenAI service integration.
"""

from unittest.mock import Mock, patch

from src.service_integrations.openai import OpenAIServiceIntegration


class TestOpenAIServiceIntegration:
    """Tests for the OpenAIServiceIntegration class."""

    def test_get_name(self):
        """Test that service name is correct."""
        service = OpenAIServiceIntegration()
        assert service.get_name() == "OpenAI"

    @patch("src.service_integrations.openai.get_config")
    def test_is_configured_true(self, mock_get_config):
        """Test is_configured returns True when API key is set."""
        config = Mock()
        config.openai.openai_api_key = "test-api-key"
        mock_get_config.return_value = config

        service = OpenAIServiceIntegration()
        assert service.is_configured() is True

    @patch("src.service_integrations.openai.get_config")
    def test_is_configured_false(self, mock_get_config):
        """Test is_configured returns False when API key is empty."""
        config = Mock()
        config.openai.openai_api_key = ""
        mock_get_config.return_value = config

        service = OpenAIServiceIntegration()
        assert service.is_configured() is False

    @patch("src.service_integrations.openai.get_config")
    def test_is_configured_false_none(self, mock_get_config):
        """Test is_configured returns False when API key is None."""
        config = Mock()
        config.openai.openai_api_key = None
        mock_get_config.return_value = config

        service = OpenAIServiceIntegration()
        assert service.is_configured() is False

    @patch("src.service_integrations.openai.update_config")
    @patch("src.service_integrations.openai.questionary.password")
    @patch("src.service_integrations.openai.questionary.confirm")
    def test_setup_basic(self, mock_confirm, mock_password, mock_update_config):
        """Test basic setup with no custom options."""
        # Mock user input
        mock_password.return_value.ask.return_value = "test-api-key"
        mock_confirm.return_value.ask.side_effect = [
            False,
            False,
        ]  # No custom URL, no custom models

        service = OpenAIServiceIntegration()
        service.setup()

        # Verify API key was saved
        mock_update_config.assert_any_call("OPENAI_API_KEY", "test-api-key")
        mock_update_config.assert_any_call(
            "OPENAI_BASE_URL", "https://api.openai.com/v1"
        )

    @patch("src.service_integrations.openai.update_config")
    @patch("src.service_integrations.openai.questionary.password")
    @patch("src.service_integrations.openai.questionary.confirm")
    @patch("src.service_integrations.openai.questionary.text")
    def test_setup_with_custom_url(
        self, mock_text, mock_confirm, mock_password, mock_update_config
    ):
        """Test setup with custom base URL."""
        # Mock user input
        mock_password.return_value.ask.return_value = "test-api-key"
        mock_confirm.return_value.ask.side_effect = [
            True,
            False,
        ]  # Yes custom URL, no custom models
        mock_text.return_value.ask.return_value = "https://custom.openai.com/v1"

        service = OpenAIServiceIntegration()
        service.setup()

        mock_update_config.assert_any_call("OPENAI_API_KEY", "test-api-key")
        mock_update_config.assert_any_call(
            "OPENAI_BASE_URL", "https://custom.openai.com/v1"
        )

    @patch("src.service_integrations.openai.update_config")
    @patch("src.service_integrations.openai.questionary.password")
    @patch("src.service_integrations.openai.questionary.confirm")
    @patch("src.service_integrations.openai.questionary.text")
    def test_setup_with_custom_models(
        self, mock_text, mock_confirm, mock_password, mock_update_config
    ):
        """Test setup with custom model configuration."""
        # Mock user input
        mock_password.return_value.ask.return_value = "test-api-key"
        mock_confirm.return_value.ask.side_effect = [
            False,
            True,
        ]  # No custom URL, custom models
        mock_text.return_value.ask.side_effect = [
            "gpt-4-turbo",  # workitem model
            "gpt-4",  # overall model
        ]

        service = OpenAIServiceIntegration()
        service.setup()

        mock_update_config.assert_any_call("OPENAI_API_KEY", "test-api-key")
        mock_update_config.assert_any_call(
            "OPENAI_WORKITEM_SUMMARY_MODEL", "gpt-4-turbo"
        )
        mock_update_config.assert_any_call("OPENAI_SUMMARY_MODEL", "gpt-4")

    @patch("src.service_integrations.openai.update_config")
    @patch("src.service_integrations.openai.questionary.password")
    @patch("src.service_integrations.openai.questionary.confirm")
    @patch("src.service_integrations.openai.questionary.text")
    def test_setup_with_all_custom_options(
        self, mock_text, mock_confirm, mock_password, mock_update_config
    ):
        """Test setup with all custom options enabled."""
        # Mock user input
        mock_password.return_value.ask.return_value = "test-api-key"
        mock_confirm.return_value.ask.side_effect = [
            True,
            True,
        ]  # Yes custom URL, yes custom models
        mock_text.return_value.ask.side_effect = [
            "https://azure.openai.com/v1",  # custom base URL
            "gpt-4-turbo",  # workitem model
            "gpt-4",  # overall model
        ]

        service = OpenAIServiceIntegration()
        service.setup()

        mock_update_config.assert_any_call("OPENAI_API_KEY", "test-api-key")
        mock_update_config.assert_any_call(
            "OPENAI_BASE_URL", "https://azure.openai.com/v1"
        )
        mock_update_config.assert_any_call(
            "OPENAI_WORKITEM_SUMMARY_MODEL", "gpt-4-turbo"
        )
        mock_update_config.assert_any_call("OPENAI_SUMMARY_MODEL", "gpt-4")

    @patch("src.service_integrations.openai.get_config")
    def test_validate_not_configured(self, mock_get_config):
        """Test validate when service is not configured."""
        config = Mock()
        config.openai.openai_api_key = ""
        mock_get_config.return_value = config

        service = OpenAIServiceIntegration()
        result = service.validate()

        assert result is False

    @patch("src.service_integrations.openai.get_config")
    @patch("src.service_integrations.openai.OpenAI")
    def test_validate_success(self, mock_openai_class, mock_get_config):
        """Test successful validation."""
        config = Mock()
        config.openai.openai_api_key = "test-api-key"
        config.openai.openai_base_url = "https://api.openai.com/v1"
        mock_get_config.return_value = config

        mock_client = Mock()
        mock_client.models.list.return_value = []
        mock_openai_class.return_value = mock_client

        service = OpenAIServiceIntegration()
        result = service.validate()

        assert result is True
        mock_openai_class.assert_called_once_with(
            base_url="https://api.openai.com/v1",
            api_key="test-api-key",
        )
        mock_client.models.list.assert_called_once()

    @patch("src.service_integrations.openai.get_config")
    @patch("src.service_integrations.openai.OpenAI")
    def test_validate_failure(self, mock_openai_class, mock_get_config):
        """Test validation failure when API call fails."""
        config = Mock()
        config.openai.openai_api_key = "test-api-key"
        config.openai.openai_base_url = "https://api.openai.com/v1"
        mock_get_config.return_value = config

        mock_openai_class.side_effect = Exception("API connection failed")

        service = OpenAIServiceIntegration()
        result = service.validate()

        assert result is False

    @patch("src.service_integrations.openai.update_config")
    def test_disconnect(self, mock_update_config):
        """Test disconnecting OpenAI service."""
        service = OpenAIServiceIntegration()
        service.disconnect()

        assert mock_update_config.call_count == 4
        mock_update_config.assert_any_call("OPENAI_API_KEY", "")
        mock_update_config.assert_any_call(
            "OPENAI_BASE_URL", "https://api.openai.com/v1"
        )
        mock_update_config.assert_any_call(
            "OPENAI_WORKITEM_SUMMARY_MODEL", "gpt-4o-mini"
        )
        mock_update_config.assert_any_call("OPENAI_SUMMARY_MODEL", "gpt-5")

    @patch("src.service_integrations.openai.get_config")
    @patch("src.service_integrations.openai.OpenAI")
    def test_validate_with_custom_base_url(self, mock_openai_class, mock_get_config):
        """Test validation with custom base URL."""
        config = Mock()
        config.openai.openai_api_key = "test-api-key"
        config.openai.openai_base_url = "https://custom.openai.com/v1"
        mock_get_config.return_value = config

        mock_client = Mock()
        mock_client.models.list.return_value = []
        mock_openai_class.return_value = mock_client

        service = OpenAIServiceIntegration()
        result = service.validate()

        assert result is True
        mock_openai_class.assert_called_once_with(
            base_url="https://custom.openai.com/v1",
            api_key="test-api-key",
        )
