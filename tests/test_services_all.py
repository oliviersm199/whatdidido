"""Tests for ConfigService, CleanService, DisconnectService, and ConnectService."""

from unittest.mock import Mock

from src.services.clean_service import CleanService
from src.services.config_service import ConfigService
from src.services.connect_service import ConnectService
from src.services.disconnect_service import DisconnectService


class TestConfigService:
    """Tests for ConfigService."""

    def test_file_exists_true(self, tmp_path):
        """Test file_exists returns True when file exists."""
        config_file = tmp_path / "config.env"
        config_file.write_text("KEY=value\n")

        service = ConfigService(config_file)
        assert service.file_exists() is True

    def test_file_exists_false(self, tmp_path):
        """Test file_exists returns False when file doesn't exist."""
        config_file = tmp_path / "nonexistent.env"

        service = ConfigService(config_file)
        assert service.file_exists() is False

    def test_is_empty_true(self, tmp_path):
        """Test is_empty returns True for empty file."""
        config_file = tmp_path / "config.env"
        config_file.write_text("")

        service = ConfigService(config_file)
        assert service.is_empty() is True

    def test_is_empty_false(self, tmp_path):
        """Test is_empty returns False for file with content."""
        config_file = tmp_path / "config.env"
        config_file.write_text("KEY=value\n")

        service = ConfigService(config_file)
        assert service.is_empty() is False

    def test_anonymize_value_long(self, tmp_path):
        """Test anonymizing a long value."""
        service = ConfigService(tmp_path / "config.env")
        result = service.anonymize_value("abcdefghijklmnop")

        assert result == "abcd...mnop"

    def test_anonymize_value_short(self, tmp_path):
        """Test anonymizing a short value."""
        service = ConfigService(tmp_path / "config.env")
        result = service.anonymize_value("short")

        assert result == "****"

    def test_anonymize_value_empty(self, tmp_path):
        """Test anonymizing an empty value."""
        service = ConfigService(tmp_path / "config.env")
        result = service.anonymize_value("")

        assert result == ""

    def test_is_sensitive_key_true(self, tmp_path):
        """Test identifying sensitive keys."""
        service = ConfigService(tmp_path / "config.env")

        assert service.is_sensitive_key("OPENAI_API_KEY") is True
        assert service.is_sensitive_key("JIRA_TOKEN") is True
        assert service.is_sensitive_key("MY_PASSWORD") is True

    def test_is_sensitive_key_false(self, tmp_path):
        """Test identifying non-sensitive keys."""
        service = ConfigService(tmp_path / "config.env")

        assert service.is_sensitive_key("JIRA_URL") is False
        assert service.is_sensitive_key("USERNAME") is False

    def test_get_config_lines_with_sensitive_data(self, tmp_path):
        """Test getting config lines with sensitive data anonymized."""
        config_file = tmp_path / "config.env"
        config_file.write_text(
            "JIRA_URL=https://test.atlassian.net\n"
            "JIRA_API_KEY=secret123456789\n"
            "JIRA_USERNAME=user@example.com\n"
        )

        service = ConfigService(config_file)
        lines = service.get_config_lines()

        assert len(lines) == 3
        assert lines[0] == "JIRA_URL=https://test.atlassian.net"
        assert lines[1] == "JIRA_API_KEY=secr...6789"
        assert lines[2] == "JIRA_USERNAME=user@example.com"

    def test_get_config_lines_with_comments(self, tmp_path):
        """Test getting config lines preserves comments."""
        config_file = tmp_path / "config.env"
        config_file.write_text("# Comment\nKEY=value\n\n")

        service = ConfigService(config_file)
        lines = service.get_config_lines()

        assert lines[0] == "# Comment"
        assert lines[1] == "KEY=value"
        assert lines[2] == ""

    def test_is_empty_when_file_not_exists(self, tmp_path):
        """Test is_empty returns True when file doesn't exist."""
        config_file = tmp_path / "nonexistent.env"

        service = ConfigService(config_file)
        assert service.is_empty() is True

    def test_get_config_lines_when_file_not_exists(self, tmp_path):
        """Test get_config_lines returns empty list when file doesn't exist."""
        config_file = tmp_path / "nonexistent.env"

        service = ConfigService(config_file)
        lines = service.get_config_lines()

        assert lines == []

    def test_get_config_lines_with_empty_sensitive_value(self, tmp_path):
        """Test getting config lines with empty sensitive value."""
        config_file = tmp_path / "config.env"
        config_file.write_text("JIRA_API_KEY=\nJIRA_URL=https://test.com\n")

        service = ConfigService(config_file)
        lines = service.get_config_lines()

        assert lines[0] == "JIRA_API_KEY="
        assert lines[1] == "JIRA_URL=https://test.com"

    def test_get_config_lines_with_no_equals_sign(self, tmp_path):
        """Test getting config lines with lines that don't have = sign."""
        config_file = tmp_path / "config.env"
        config_file.write_text("JIRA_URL=https://test.com\nSome text without equals\n")

        service = ConfigService(config_file)
        lines = service.get_config_lines()

        assert lines[0] == "JIRA_URL=https://test.com"
        assert lines[1] == "Some text without equals"


class TestCleanService:
    """Tests for CleanService."""

    def test_get_files_to_clean_none_exist(self, tmp_path):
        """Test getting files to clean when none exist."""
        service = CleanService(base_dir=tmp_path)
        files = service.get_files_to_clean()

        assert files == []

    def test_get_files_to_clean_some_exist(self, tmp_path):
        """Test getting files to clean when some exist."""
        (tmp_path / "whatdidido.json").write_text("{}")
        (tmp_path / "whatdidido.md").write_text("# Report")

        service = CleanService(base_dir=tmp_path)
        files = service.get_files_to_clean()

        assert len(files) == 2
        assert tmp_path / "whatdidido.json" in files
        assert tmp_path / "whatdidido.md" in files

    def test_clean_success(self, tmp_path):
        """Test successful clean operation."""
        (tmp_path / "whatdidido.json").write_text("{}")
        (tmp_path / "whatdidido.md").write_text("# Report")

        service = CleanService(base_dir=tmp_path)
        result = service.clean()

        assert result.success is True
        assert len(result.deleted_files) == 2
        assert len(result.errors) == 0
        assert not (tmp_path / "whatdidido.json").exists()
        assert not (tmp_path / "whatdidido.md").exists()

    def test_clean_no_files(self, tmp_path):
        """Test clean when no files exist."""
        service = CleanService(base_dir=tmp_path)
        result = service.clean()

        assert result.success is True
        assert len(result.deleted_files) == 0
        assert len(result.errors) == 0

    def test_clean_with_error(self, tmp_path):
        """Test clean when deletion fails for a file."""
        # Create a file but make it undeletable by making the directory read-only
        data_file = tmp_path / "whatdidido.json"
        data_file.write_text("{}")

        # Make the directory read-only (on Unix-like systems)
        import os
        import stat

        os.chmod(tmp_path, stat.S_IRUSR | stat.S_IXUSR)

        try:
            service = CleanService(base_dir=tmp_path)
            result = service.clean()

            # Should have errors
            assert result.success is False
            assert len(result.errors) > 0
            assert data_file in result.errors
        finally:
            # Restore write permissions
            os.chmod(tmp_path, stat.S_IRWXU)


class TestDisconnectService:
    """Tests for DisconnectService."""

    def test_get_configured_providers(self):
        """Test getting configured providers."""
        mock_class1 = Mock()
        mock_instance1 = Mock()
        mock_instance1.is_configured.return_value = True
        mock_class1.return_value = mock_instance1

        mock_class2 = Mock()
        mock_instance2 = Mock()
        mock_instance2.is_configured.return_value = False
        mock_class2.return_value = mock_instance2

        service = DisconnectService()
        providers = service.get_configured_providers([mock_class1, mock_class2])

        assert len(providers) == 1
        assert providers[0] is mock_instance1

    def test_disconnect_providers_success(self):
        """Test disconnecting providers successfully."""
        mock_provider1 = Mock()
        mock_provider1.get_name.return_value = "Jira"
        mock_provider1.disconnect.return_value = None

        mock_provider2 = Mock()
        mock_provider2.get_name.return_value = "Linear"
        mock_provider2.disconnect.return_value = None

        service = DisconnectService()
        disconnected, errors = service.disconnect_providers(
            [mock_provider1, mock_provider2]
        )

        assert disconnected == ["Jira", "Linear"]
        assert errors == {}

    def test_disconnect_providers_with_error(self):
        """Test disconnecting providers with one failing."""
        mock_provider1 = Mock()
        mock_provider1.get_name.return_value = "Jira"
        mock_provider1.disconnect.return_value = None

        mock_provider2 = Mock()
        mock_provider2.get_name.return_value = "Linear"
        mock_provider2.disconnect.side_effect = Exception("Disconnect failed")

        service = DisconnectService()
        disconnected, errors = service.disconnect_providers(
            [mock_provider1, mock_provider2]
        )

        assert disconnected == ["Jira"]
        assert errors == {"Linear": "Disconnect failed"}

    def test_disconnect_services_with_error(self):
        """Test disconnecting services with one failing."""
        mock_service1 = Mock()
        mock_service1.get_name.return_value = "OpenAI"
        mock_service1.disconnect.return_value = None

        mock_service2 = Mock()
        mock_service2.get_name.return_value = "Slack"
        mock_service2.disconnect.side_effect = Exception("Disconnect failed")

        service = DisconnectService()
        disconnected, errors = service.disconnect_services(
            [mock_service1, mock_service2]
        )

        assert disconnected == ["OpenAI"]
        assert errors == {"Slack": "Disconnect failed"}

    def test_disconnect_all_providers_and_services(self):
        """Test disconnecting both providers and services."""
        mock_provider_class = Mock()
        mock_provider = Mock()
        mock_provider.is_configured.return_value = True
        mock_provider.get_name.return_value = "Jira"
        mock_provider.disconnect.return_value = None
        mock_provider_class.return_value = mock_provider

        mock_service_class = Mock()
        mock_service = Mock()
        mock_service.is_configured.return_value = True
        mock_service.get_name.return_value = "OpenAI"
        mock_service.disconnect.return_value = None
        mock_service_class.return_value = mock_service

        service = DisconnectService()
        result = service.disconnect_all(
            provider_classes=[mock_provider_class],
            service_classes=[mock_service_class],
        )

        assert result.disconnected_providers == ["Jira"]
        assert result.disconnected_services == ["OpenAI"]
        assert result.total_disconnected == 2
        assert result.success is True


class TestConnectService:
    """Tests for ConnectService."""

    def test_setup_provider_success(self):
        """Test setting up a provider successfully."""
        mock_provider = Mock()
        mock_provider.get_name.return_value = "Jira"
        mock_provider.setup.return_value = None

        service = ConnectService()
        name, error = service.setup_provider(mock_provider)

        assert name == "Jira"
        assert error is None
        mock_provider.setup.assert_called_once()

    def test_setup_provider_failure(self):
        """Test setting up a provider that fails."""
        mock_provider = Mock()
        mock_provider.get_name.return_value = "Jira"
        mock_provider.setup.side_effect = Exception("Setup failed")

        service = ConnectService()
        name, error = service.setup_provider(mock_provider)

        assert name == "Jira"
        assert error == "Setup failed"

    def test_setup_service_success(self):
        """Test setting up a service successfully."""
        mock_service = Mock()
        mock_service.get_name.return_value = "OpenAI"
        mock_service.setup.return_value = None

        service = ConnectService()
        name, error = service.setup_service(mock_service)

        assert name == "OpenAI"
        assert error is None

    def test_validate_service_success(self):
        """Test validating a service successfully."""
        mock_service = Mock()
        mock_service.get_name.return_value = "OpenAI"
        mock_service.validate.return_value = True

        service = ConnectService()
        name, is_valid, error = service.validate_service(mock_service)

        assert name == "OpenAI"
        assert is_valid is True
        assert error is None

    def test_validate_service_failure(self):
        """Test validating a service that fails."""
        mock_service = Mock()
        mock_service.get_name.return_value = "OpenAI"
        mock_service.validate.return_value = False

        service = ConnectService()
        name, is_valid, error = service.validate_service(mock_service)

        assert name == "OpenAI"
        assert is_valid is False
        assert error is None

    def test_setup_providers_all_success(self):
        """Test setting up multiple providers successfully."""
        mock_provider1 = Mock()
        mock_provider1.get_name.return_value = "Jira"
        mock_provider1.setup.return_value = None

        mock_provider2 = Mock()
        mock_provider2.get_name.return_value = "Linear"
        mock_provider2.setup.return_value = None

        service = ConnectService()
        configured, errors = service.setup_providers([mock_provider1, mock_provider2])

        assert configured == ["Jira", "Linear"]
        assert errors == {}

    def test_setup_providers_with_error(self):
        """Test setting up providers when one fails."""
        mock_provider1 = Mock()
        mock_provider1.get_name.return_value = "Jira"
        mock_provider1.setup.return_value = None

        mock_provider2 = Mock()
        mock_provider2.get_name.return_value = "Linear"
        mock_provider2.setup.side_effect = Exception("Setup failed")

        service = ConnectService()
        configured, errors = service.setup_providers([mock_provider1, mock_provider2])

        assert configured == ["Jira"]
        assert "Linear" in errors
        assert errors["Linear"] == "Setup failed"

    def test_setup_services_with_validation(self):
        """Test setting up services with validation enabled."""
        mock_service = Mock()
        mock_service.get_name.return_value = "OpenAI"
        mock_service.setup.return_value = None
        mock_service.validate.return_value = True

        service = ConnectService()
        configured, errors = service.setup_services([mock_service], validate=True)

        assert configured == ["OpenAI"]
        assert errors == {}
        mock_service.validate.assert_called_once()

    def test_setup_services_validation_fails(self):
        """Test setting up services when validation fails."""
        mock_service = Mock()
        mock_service.get_name.return_value = "OpenAI"
        mock_service.setup.return_value = None
        mock_service.validate.return_value = False

        service = ConnectService()
        configured, errors = service.setup_services([mock_service], validate=True)

        assert configured == []
        assert "OpenAI" in errors

    def test_setup_service_failure(self):
        """Test setting up a service that raises an exception."""
        mock_service = Mock()
        mock_service.get_name.return_value = "OpenAI"
        mock_service.setup.side_effect = Exception("Setup error")

        service = ConnectService()
        name, error = service.setup_service(mock_service)

        assert name == "OpenAI"
        assert error == "Setup error"

    def test_validate_service_exception(self):
        """Test validating a service that raises an exception."""
        mock_service = Mock()
        mock_service.get_name.return_value = "OpenAI"
        mock_service.validate.side_effect = Exception("Validation error")

        service = ConnectService()
        name, is_valid, error = service.validate_service(mock_service)

        assert name == "OpenAI"
        assert is_valid is False
        assert error == "Validation error"

    def test_setup_services_validation_exception(self):
        """Test setting up services when validation raises an exception."""
        mock_service = Mock()
        mock_service.get_name.return_value = "OpenAI"
        mock_service.setup.return_value = None
        mock_service.validate.side_effect = Exception("Validation failed")

        service = ConnectService()
        configured, errors = service.setup_services([mock_service], validate=True)

        assert configured == []
        assert "OpenAI" in errors
        assert errors["OpenAI"] == "Validation failed"

    def test_setup_services_with_setup_error(self):
        """Test setting up services when setup fails."""
        mock_service = Mock()
        mock_service.get_name.return_value = "OpenAI"
        mock_service.setup.side_effect = Exception("Setup error")

        service = ConnectService()
        configured, errors = service.setup_services([mock_service], validate=False)

        assert configured == []
        assert "OpenAI" in errors
        assert errors["OpenAI"] == "Setup error"
