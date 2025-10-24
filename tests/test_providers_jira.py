"""
Tests for the Jira provider.
"""

from unittest.mock import Mock, patch

from src.providers.jira import JiraProvider


class TestJiraProvider:
    """Tests for the JiraProvider class."""

    def test_get_name(self):
        """Test that provider name is correct."""
        provider = JiraProvider()
        assert provider.get_name() == "Jira"

    @patch("src.providers.jira.get_config")
    def test_is_configured_true(self, mock_get_config, mock_jira_config):
        """Test is_configured returns True when all credentials are set."""
        mock_get_config.return_value = mock_jira_config
        provider = JiraProvider()

        assert provider.is_configured() is True

    @patch("src.providers.jira.get_config")
    def test_is_configured_false_missing_url(self, mock_get_config):
        """Test is_configured returns False when URL is missing."""
        config = Mock()
        config.jira.jira_url = ""
        config.jira.jira_username = "test@example.com"
        config.jira.jira_api_key = "test-key"
        mock_get_config.return_value = config

        provider = JiraProvider()
        assert provider.is_configured() is False

    @patch("src.providers.jira.get_config")
    def test_is_configured_false_missing_username(self, mock_get_config):
        """Test is_configured returns False when username is missing."""
        config = Mock()
        config.jira.jira_url = "https://test.atlassian.net"
        config.jira.jira_username = ""
        config.jira.jira_api_key = "test-key"
        mock_get_config.return_value = config

        provider = JiraProvider()
        assert provider.is_configured() is False

    @patch("src.providers.jira.get_config")
    def test_is_configured_false_missing_api_key(self, mock_get_config):
        """Test is_configured returns False when API key is missing."""
        config = Mock()
        config.jira.jira_url = "https://test.atlassian.net"
        config.jira.jira_username = "test@example.com"
        config.jira.jira_api_key = ""
        mock_get_config.return_value = config

        provider = JiraProvider()
        assert provider.is_configured() is False

    @patch("src.providers.jira.get_config")
    @patch("src.providers.jira.jira.JIRA")
    @patch("src.providers.jira.logger")
    def test_authenticate_success(
        self, mock_echo, mock_jira_class, mock_get_config, mock_jira_config
    ):
        """Test successful authentication with Jira."""
        mock_get_config.return_value = mock_jira_config

        mock_jira_client = Mock()
        mock_jira_client.server_info.return_value = {"version": "8.0.0"}
        mock_jira_class.return_value = mock_jira_client

        provider = JiraProvider()
        result = provider.authenticate()

        assert result is True
        assert provider.jira_client is mock_jira_client
        mock_jira_class.assert_called_once_with(
            server="https://test.atlassian.net",
            basic_auth=("test@example.com", "test-api-key"),
            timeout=25,
        )

    @patch("src.providers.jira.get_config")
    @patch("src.providers.jira.jira.JIRA")
    @patch("src.providers.jira.logger")
    def test_authenticate_failure(
        self, mock_echo, mock_jira_class, mock_get_config, mock_jira_config
    ):
        """Test failed authentication with Jira."""
        mock_get_config.return_value = mock_jira_config

        from jira import JIRAError

        mock_jira_class.side_effect = JIRAError("Authentication failed")

        provider = JiraProvider()
        result = provider.authenticate()

        assert result is False

    @patch("src.providers.jira.get_config")
    @patch("src.providers.jira.jira.JIRA")
    @patch("src.providers.jira.logger")
    def test_fetch_items_with_user_filter(
        self,
        mock_echo,
        mock_jira_class,
        mock_get_config,
        mock_jira_config,
        mock_jira_issue,
        sample_fetch_params,
    ):
        """Test fetching items with user filter."""
        mock_get_config.return_value = mock_jira_config

        mock_jira_client = Mock()
        mock_jira_client.server_url = "https://test.atlassian.net"
        mock_jira_client.server_info.return_value = {"version": "8.0.0"}
        mock_jira_client.search_issues.return_value = [mock_jira_issue]
        mock_jira_class.return_value = mock_jira_client

        provider = JiraProvider()
        provider.authenticate()

        items = list(provider.fetch_items(sample_fetch_params))

        assert len(items) == 1
        assert items[0].id == "TEST-123"
        assert items[0].title == "Test Jira Issue"
        assert items[0].provider == "Jira"

        # Verify JQL query includes user filter
        call_args = mock_jira_client.search_issues.call_args
        jql_query = call_args[0][0]
        assert "user@example.com" in jql_query

    @patch("src.providers.jira.get_config")
    @patch("src.providers.jira.jira.JIRA")
    @patch("src.providers.jira.logger")
    def test_fetch_items_without_user_filter(
        self,
        mock_echo,
        mock_jira_class,
        mock_get_config,
        mock_jira_config,
        mock_jira_issue,
        fetch_params_no_user,
    ):
        """Test fetching items without user filter (currentUser)."""
        mock_get_config.return_value = mock_jira_config

        mock_jira_client = Mock()
        mock_jira_client.server_url = "https://test.atlassian.net"
        mock_jira_client.server_info.return_value = {"version": "8.0.0"}
        mock_jira_client.search_issues.return_value = [mock_jira_issue]
        mock_jira_class.return_value = mock_jira_client

        provider = JiraProvider()
        provider.authenticate()

        items = list(provider.fetch_items(fetch_params_no_user))

        assert len(items) == 1

        # Verify JQL query uses currentUser()
        call_args = mock_jira_client.search_issues.call_args
        jql_query = call_args[0][0]
        assert "currentUser()" in jql_query

    @patch("src.providers.jira.get_config")
    @patch("src.providers.jira.jira.JIRA")
    @patch("src.providers.jira.logger")
    def test_fetch_items_pagination(
        self,
        mock_echo,
        mock_jira_class,
        mock_get_config,
        mock_jira_config,
        mock_jira_issue,
        sample_fetch_params,
    ):
        """Test fetching items with pagination."""
        mock_get_config.return_value = mock_jira_config

        mock_jira_client = Mock()
        mock_jira_client.server_url = "https://test.atlassian.net"
        mock_jira_client.server_info.return_value = {"version": "8.0.0"}

        # First call returns 50 items, second call returns empty
        mock_jira_client.search_issues.side_effect = [
            [mock_jira_issue] * 50,  # Full page
            [],  # Empty (end of results)
        ]
        mock_jira_class.return_value = mock_jira_client

        provider = JiraProvider()
        provider.authenticate()

        items = list(provider.fetch_items(sample_fetch_params))

        assert len(items) == 50
        assert mock_jira_client.search_issues.call_count == 2

    @patch("src.providers.jira.get_config")
    @patch("src.providers.jira.jira.JIRA")
    @patch("src.providers.jira.logger")
    def test_fetch_items_no_authentication(
        self,
        mock_echo,
        mock_jira_class,
        mock_get_config,
        mock_jira_config,
        sample_fetch_params,
    ):
        """Test fetching items triggers authentication if not authenticated."""
        mock_get_config.return_value = mock_jira_config

        mock_jira_client = Mock()
        mock_jira_client.server_url = "https://test.atlassian.net"
        mock_jira_client.server_info.return_value = {"version": "8.0.0"}
        mock_jira_client.search_issues.return_value = []
        mock_jira_class.return_value = mock_jira_client

        provider = JiraProvider()
        # Don't authenticate first

        list(provider.fetch_items(sample_fetch_params))

        # Should have authenticated automatically
        assert hasattr(provider, "jira_client")

    def test_convert_jira_issue_to_work_item(self, mock_jira_issue):
        """Test converting Jira issue to WorkItem."""
        provider = JiraProvider()
        provider.jira_client = Mock()
        provider.jira_client.server_url = "https://test.atlassian.net"

        work_item = provider._convert_jira_issue_to_work_item(mock_jira_issue)

        assert work_item.id == "TEST-123"
        assert work_item.title == "Test Jira Issue"
        assert work_item.description == "Test description"
        assert work_item.url == "https://test.atlassian.net/browse/TEST-123"
        assert work_item.provider == "Jira"

        # Verify raw_data contains Jira-specific fields
        assert work_item.raw_data["status"] == "In Progress"
        assert work_item.raw_data["issue_type"] == "Task"
        assert work_item.raw_data["priority"] == "Medium"
        assert work_item.raw_data["assignee"]["email"] == "test@example.com"
        assert work_item.raw_data["reporter"]["email"] == "reporter@example.com"
        assert work_item.raw_data["project"]["key"] == "TEST"
        assert work_item.raw_data["labels"] == ["bug", "urgent"]

    def test_convert_jira_issue_with_comments(self, mock_jira_issue):
        """Test converting Jira issue with comments."""
        # Add comments to the mock issue
        comment1 = Mock()
        comment1.id = "comment-1"
        comment1.body = "First comment"
        comment1.created = "2025-01-16T10:00:00.000+0000"
        comment1.updated = "2025-01-16T10:00:00.000+0000"
        comment1.author = Mock()
        comment1.author.displayName = "Commenter"
        comment1.author.name = "commenter"
        comment1.author.emailAddress = "commenter@example.com"

        mock_jira_issue.fields.comment.comments = [comment1]

        provider = JiraProvider()
        provider.jira_client = Mock()
        provider.jira_client.server_url = "https://test.atlassian.net"

        work_item = provider._convert_jira_issue_to_work_item(mock_jira_issue)

        assert work_item.raw_data["comments"]["count"] == 1
        assert work_item.raw_data["comments"]["last_comment_author"] == "Commenter"
        assert len(work_item.raw_data["comments"]["comments"]) == 1

    def test_convert_jira_issue_minimal(self):
        """Test converting Jira issue with minimal fields."""
        issue = Mock()
        issue.key = "MIN-1"
        issue.fields = Mock()
        issue.fields.summary = "Minimal issue"
        issue.fields.description = None
        issue.fields.created = "2025-01-01T00:00:00.000+0000"
        issue.fields.updated = "2025-01-01T00:00:00.000+0000"
        issue.fields.status = Mock()
        issue.fields.status.name = "Open"
        issue.fields.issuetype = Mock()
        issue.fields.issuetype.name = "Bug"
        issue.fields.assignee = None
        issue.fields.reporter = None
        issue.fields.creator = None
        issue.fields.priority = None
        issue.fields.project = None
        issue.fields.labels = []
        issue.fields.components = []
        issue.fields.subtasks = []
        issue.fields.parent = None
        issue.fields.comment = None
        issue.fields.resolution = None
        issue.fields.timetracking = None

        provider = JiraProvider()
        provider.jira_client = Mock()
        provider.jira_client.server_url = "https://test.atlassian.net"

        work_item = provider._convert_jira_issue_to_work_item(issue)

        assert work_item.id == "MIN-1"
        assert work_item.title == "Minimal issue"
        assert work_item.description == ""
        assert work_item.raw_data["assignee"] is None
        assert work_item.raw_data["priority"] is None

    @patch("src.providers.jira.update_config")
    def test_disconnect(self, mock_update_config):
        """Test disconnecting Jira provider."""
        provider = JiraProvider()
        provider.disconnect()

        assert mock_update_config.call_count == 3
        mock_update_config.assert_any_call("JIRA_URL", "")
        mock_update_config.assert_any_call("JIRA_USERNAME", "")
        mock_update_config.assert_any_call("JIRA_API_KEY", "")

    @patch("src.providers.jira.questionary.text")
    @patch("src.providers.jira.questionary.password")
    def test_ask_jira_credentials(self, mock_password, mock_text):
        """Test asking for Jira credentials."""
        from src.providers.jira import ask_jira_credentials

        mock_text.return_value.ask.side_effect = [
            "https://test.atlassian.net",
            "test@example.com",
        ]
        mock_password.return_value.ask.return_value = "test-api-key"

        credentials = ask_jira_credentials()

        assert credentials["server"] == "https://test.atlassian.net"
        assert credentials["username"] == "test@example.com"
        assert credentials["api_token"] == "test-api-key"
