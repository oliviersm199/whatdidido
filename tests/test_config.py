"""Unit tests for the config module."""

import os
from unittest.mock import patch

from config import (
    Config,
    JiraConfig,
    LinearConfig,
    OpenAIConfig,
    get_config,
    update_config,
)


class TestConfigModels:
    """Test Pydantic config models."""

    def test_jira_config_creation(self):
        """Test JiraConfig model creation."""
        config = JiraConfig(
            jira_url="https://example.atlassian.net",
            jira_username="user@example.com",
            jira_api_key="test_key",
        )
        assert config.jira_url == "https://example.atlassian.net"
        assert config.jira_username == "user@example.com"
        assert config.jira_api_key == "test_key"

    def test_linear_config_creation(self):
        """Test LinearConfig model creation."""
        config = LinearConfig(linear_api_key="lin_api_key")
        assert config.linear_api_key == "lin_api_key"

    def test_openai_config_defaults(self):
        """Test OpenAIConfig with default values."""
        config = OpenAIConfig(openai_api_key="sk-test-key")
        assert config.openai_api_key == "sk-test-key"
        assert config.openai_base_url == "https://api.openai.com/v1"
        assert config.openai_workitem_summary_model == "gpt-4o-mini"
        assert config.openai_summary_model == "gpt-5"

    def test_openai_config_custom_values(self):
        """Test OpenAIConfig with custom values."""
        config = OpenAIConfig(
            openai_api_key="sk-test-key",
            openai_base_url="https://custom.openai.com/v1",
            openai_workitem_summary_model="gpt-3.5-turbo",
            openai_summary_model="gpt-4-turbo",
        )
        assert config.openai_api_key == "sk-test-key"
        assert config.openai_base_url == "https://custom.openai.com/v1"
        assert config.openai_workitem_summary_model == "gpt-3.5-turbo"
        assert config.openai_summary_model == "gpt-4-turbo"

    def test_config_creation(self):
        """Test main Config model creation."""
        config = Config(
            jira=JiraConfig(
                jira_url="https://example.atlassian.net",
                jira_username="user@example.com",
                jira_api_key="jira_key",
            ),
            linear=LinearConfig(linear_api_key="linear_key"),
            openai=OpenAIConfig(openai_api_key="openai_key"),
        )
        assert config.jira.jira_url == "https://example.atlassian.net"
        assert config.linear.linear_api_key == "linear_key"
        assert config.openai.openai_api_key == "openai_key"


class TestGetConfig:
    """Test the get_config function."""

    @patch.dict(
        os.environ,
        {
            "JIRA_URL": "https://test.atlassian.net",
            "JIRA_USERNAME": "test@example.com",
            "JIRA_API_KEY": "jira_test_key",
            "GITHUB_TOKEN": "gh_test_token",
            "LINEAR_API_KEY": "linear_test_key",
            "OPENAI_API_KEY": "sk-test-key",
        },
        clear=False,
    )
    def test_get_config_from_env(self, tmp_path):
        """Test get_config reads from environment variables."""
        with patch("config.CONFIG_DIR", tmp_path):
            with patch("config.CONFIG_FILE", tmp_path / "config.env"):
                config = get_config()
                assert config.jira.jira_url == "https://test.atlassian.net"
                assert config.jira.jira_username == "test@example.com"
                assert config.jira.jira_api_key == "jira_test_key"
                assert config.linear.linear_api_key == "linear_test_key"
                assert config.openai.openai_api_key == "sk-test-key"

    @patch.dict(
        os.environ,
        {
            "OPENAI_API_KEY": "sk-test-key",
            "OPENAI_BASE_URL": "https://custom.openai.com/v1",
            "OPENAI_WORKITEM_SUMMARY_MODEL": "gpt-3.5-turbo",
            "OPENAI_SUMMARY_MODEL": "gpt-4-turbo",
        },
        clear=False,
    )
    def test_get_config_openai_custom_settings(self, tmp_path):
        """Test get_config with custom OpenAI settings."""
        with patch("config.CONFIG_DIR", tmp_path):
            with patch("config.CONFIG_FILE", tmp_path / "config.env"):
                config = get_config()
                assert config.openai.openai_api_key == "sk-test-key"
                assert config.openai.openai_base_url == "https://custom.openai.com/v1"
                assert config.openai.openai_workitem_summary_model == "gpt-3.5-turbo"
                assert config.openai.openai_summary_model == "gpt-4-turbo"

    def test_get_config_creates_directory(self, tmp_path):
        """Test get_config creates config directory if it doesn't exist."""
        config_dir = tmp_path / "new_config_dir"
        config_file = config_dir / "config.env"

        with patch("config.CONFIG_DIR", config_dir):
            with patch("config.CONFIG_FILE", config_file):
                with patch.dict(os.environ, {}, clear=False):
                    get_config()
                    assert config_dir.exists()
                    assert config_file.exists()

    def test_get_config_empty_values(self, tmp_path):
        """Test get_config returns empty strings when no env vars set."""
        env_vars_to_clear = [
            "JIRA_URL",
            "JIRA_USERNAME",
            "JIRA_API_KEY",
            "GITHUB_TOKEN",
            "LINEAR_API_KEY",
            "OPENAI_API_KEY",
            "OPENAI_BASE_URL",
            "OPENAI_WORKITEM_SUMMARY_MODEL",
            "OPENAI_SUMMARY_MODEL",
        ]
        with patch("config.CONFIG_DIR", tmp_path):
            with patch("config.CONFIG_FILE", tmp_path / "config.env"):
                with patch.dict(
                    os.environ, {k: "" for k in env_vars_to_clear}, clear=False
                ):
                    config = get_config()
                    assert config.jira.jira_url == ""
                    assert config.jira.jira_username == ""
                    assert config.jira.jira_api_key == ""
                    assert config.linear.linear_api_key == ""
                    assert config.openai.openai_api_key == ""


class TestUpdateConfig:
    """Test the update_config function."""

    def test_update_config_new_key(self, tmp_path):
        """Test update_config adds a new key."""
        config_dir = tmp_path / "config_dir"
        config_file = config_dir / "config.env"

        with patch("config.CONFIG_DIR", config_dir):
            with patch("config.CONFIG_FILE", config_file):
                update_config("TEST_KEY", "test_value")
                assert config_file.exists()
                content = config_file.read_text()
                assert "TEST_KEY=test_value\n" in content

    def test_update_config_existing_key(self, tmp_path):
        """Test update_config updates an existing key."""
        config_dir = tmp_path / "config_dir"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.env"
        config_file.write_text("TEST_KEY=old_value\nOTHER_KEY=other_value\n")

        with patch("config.CONFIG_DIR", config_dir):
            with patch("config.CONFIG_FILE", config_file):
                update_config("TEST_KEY", "new_value")
                content = config_file.read_text()
                assert "TEST_KEY=new_value\n" in content
                assert "OTHER_KEY=other_value\n" in content
                assert "old_value" not in content

    def test_update_config_preserves_other_keys(self, tmp_path):
        """Test update_config preserves other keys when updating."""
        config_dir = tmp_path / "config_dir"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.env"
        original_content = "KEY1=value1\nKEY2=value2\nKEY3=value3\n"
        config_file.write_text(original_content)

        with patch("config.CONFIG_DIR", config_dir):
            with patch("config.CONFIG_FILE", config_file):
                update_config("KEY2", "new_value2")
                content = config_file.read_text()
                assert "KEY1=value1\n" in content
                assert "KEY2=new_value2\n" in content
                assert "KEY3=value3\n" in content

    def test_update_config_creates_directory(self, tmp_path):
        """Test update_config creates directory if it doesn't exist."""
        config_dir = tmp_path / "new_dir"
        config_file = config_dir / "config.env"

        with patch("config.CONFIG_DIR", config_dir):
            with patch("config.CONFIG_FILE", config_file):
                update_config("TEST_KEY", "test_value")
                assert config_dir.exists()
                assert config_file.exists()


class TestConfigIntegration:
    """Integration tests for config module."""

    def test_full_config_workflow(self, tmp_path):
        """Test a full workflow: update config, then read it."""
        config_dir = tmp_path / "workflow_test"
        config_file = config_dir / "config.env"

        # Clear environment variables to ensure clean test
        env_vars_to_clear = [
            "JIRA_URL",
            "JIRA_USERNAME",
            "JIRA_API_KEY",
            "GITHUB_TOKEN",
            "LINEAR_API_KEY",
            "OPENAI_API_KEY",
            "OPENAI_BASE_URL",
        ]

        with patch.dict(os.environ, {k: "" for k in env_vars_to_clear}, clear=False):
            with patch("config.CONFIG_DIR", config_dir):
                with patch("config.CONFIG_FILE", config_file):
                    # Update multiple config values
                    update_config("JIRA_URL", "https://workflow.atlassian.net")
                    update_config("GITHUB_TOKEN", "gh_workflow_token")
                    update_config("OPENAI_API_KEY", "sk-workflow-key")
                    update_config("OPENAI_BASE_URL", "https://workflow.openai.com/v1")

                    # Load the dotenv file manually to simulate get_config behavior
                    from dotenv import load_dotenv

                    load_dotenv(config_file, override=True)

                    # Now get config and verify
                    config = get_config()
                    assert config.jira.jira_url == "https://workflow.atlassian.net"
                    assert config.openai.openai_api_key == "sk-workflow-key"
                    assert (
                        config.openai.openai_base_url
                        == "https://workflow.openai.com/v1"
                    )
