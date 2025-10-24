"""
Tests for the Linear provider.
"""

from unittest.mock import Mock, patch

from src.providers.linear import LinearProvider


class TestLinearProvider:
    """Tests for the LinearProvider class."""

    def test_get_name(self):
        """Test that provider name is correct."""
        provider = LinearProvider()
        assert provider.get_name() == "Linear"

    @patch("src.providers.linear.get_config")
    def test_is_configured_true(self, mock_get_config, mock_linear_config):
        """Test is_configured returns True when API key is set."""
        mock_get_config.return_value = mock_linear_config
        provider = LinearProvider()

        assert provider.is_configured() is True

    @patch("src.providers.linear.get_config")
    def test_is_configured_false(self, mock_get_config):
        """Test is_configured returns False when API key is missing."""
        config = Mock()
        config.linear.linear_api_key = ""
        mock_get_config.return_value = config

        provider = LinearProvider()
        assert provider.is_configured() is False

    @patch("src.providers.linear.get_config")
    @patch("src.providers.linear.requests.post")
    def test_authenticate_success(self, mock_post, mock_get_config, mock_linear_config):
        """Test successful authentication with Linear."""
        mock_get_config.return_value = mock_linear_config

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "viewer": {
                    "id": "user-123",
                    "name": "Test User",
                    "email": "test@example.com",
                }
            }
        }
        mock_post.return_value = mock_response

        provider = LinearProvider()
        result = provider.authenticate()

        assert result is True
        assert provider.api_key == "test-linear-api-key"
        assert provider.graphql_url == "https://api.linear.app/graphql"

    @patch("src.providers.linear.get_config")
    @patch("src.providers.linear.requests.post")
    def test_authenticate_failure(self, mock_post, mock_get_config, mock_linear_config):
        """Test failed authentication with Linear."""
        mock_get_config.return_value = mock_linear_config

        mock_post.side_effect = Exception("Authentication failed")

        provider = LinearProvider()
        result = provider.authenticate()

        assert result is False

    @patch("src.providers.linear.get_config")
    @patch("src.providers.linear.requests.post")
    def test_make_graphql_request_success(
        self, mock_post, mock_get_config, mock_linear_config
    ):
        """Test making a successful GraphQL request."""
        mock_get_config.return_value = mock_linear_config

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"test": "value"}}
        mock_post.return_value = mock_response

        provider = LinearProvider()
        provider.api_key = "test-key"
        provider.graphql_url = "https://api.linear.app/graphql"

        result = provider._make_graphql_request("query { test }")

        assert result == {"data": {"test": "value"}}
        mock_post.assert_called_once()

    @patch("src.providers.linear.get_config")
    @patch("src.providers.linear.requests.post")
    def test_make_graphql_request_with_errors(
        self, mock_post, mock_get_config, mock_linear_config
    ):
        """Test GraphQL request with errors in response."""
        mock_get_config.return_value = mock_linear_config

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"errors": [{"message": "GraphQL error"}]}
        mock_post.return_value = mock_response

        provider = LinearProvider()
        provider.api_key = "test-key"
        provider.graphql_url = "https://api.linear.app/graphql"

        try:
            provider._make_graphql_request("query { test }")
            assert False, "Should have raised exception"
        except Exception as e:
            assert "GraphQL errors" in str(e)

    @patch("src.providers.linear.get_config")
    @patch("src.providers.linear.requests.post")
    def test_fetch_items_with_user_filter(
        self,
        mock_post,
        mock_get_config,
        mock_linear_config,
        mock_linear_issue,
        sample_fetch_params,
    ):
        """Test fetching items with user filter."""
        mock_get_config.return_value = mock_linear_config

        # Mock responses for user query and issues query
        user_response = Mock()
        user_response.status_code = 200
        user_response.json.return_value = {
            "data": {
                "users": {
                    "nodes": [
                        {
                            "id": "user-1",
                            "email": "user@example.com",
                            "name": "Test User",
                        }
                    ]
                }
            }
        }

        issues_response = Mock()
        issues_response.status_code = 200
        issues_response.json.return_value = {
            "data": {
                "issues": {
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [mock_linear_issue],
                }
            }
        }

        mock_post.side_effect = [user_response, issues_response]

        provider = LinearProvider()
        provider.api_key = "test-key"
        provider.graphql_url = "https://api.linear.app/graphql"

        items = list(provider.fetch_items(sample_fetch_params))

        assert len(items) == 1
        assert items[0].id == "LIN-123"
        assert items[0].title == "Test Linear Issue"
        assert items[0].provider == "Linear"

    @patch("src.providers.linear.get_config")
    @patch("src.providers.linear.requests.post")
    def test_fetch_items_without_user_filter(
        self,
        mock_post,
        mock_get_config,
        mock_linear_config,
        mock_linear_issue,
        fetch_params_no_user,
    ):
        """Test fetching items without user filter (current user)."""
        mock_get_config.return_value = mock_linear_config

        # Mock responses for viewer query and issues query
        viewer_response = Mock()
        viewer_response.status_code = 200
        viewer_response.json.return_value = {
            "data": {"viewer": {"id": "current-user-id"}}
        }

        issues_response = Mock()
        issues_response.status_code = 200
        issues_response.json.return_value = {
            "data": {
                "issues": {
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [mock_linear_issue],
                }
            }
        }

        mock_post.side_effect = [viewer_response, issues_response]

        provider = LinearProvider()
        provider.api_key = "test-key"
        provider.graphql_url = "https://api.linear.app/graphql"

        items = list(provider.fetch_items(fetch_params_no_user))

        assert len(items) == 1

    @patch("src.providers.linear.get_config")
    @patch("src.providers.linear.requests.post")
    def test_fetch_items_pagination(
        self,
        mock_post,
        mock_get_config,
        mock_linear_config,
        mock_linear_issue,
        fetch_params_no_user,
    ):
        """Test fetching items with pagination."""
        mock_get_config.return_value = mock_linear_config

        viewer_response = Mock()
        viewer_response.status_code = 200
        viewer_response.json.return_value = {
            "data": {"viewer": {"id": "current-user-id"}}
        }

        # First page
        page1_response = Mock()
        page1_response.status_code = 200
        page1_response.json.return_value = {
            "data": {
                "issues": {
                    "pageInfo": {"hasNextPage": True, "endCursor": "cursor-1"},
                    "nodes": [mock_linear_issue],
                }
            }
        }

        # Second page
        page2_response = Mock()
        page2_response.status_code = 200
        page2_response.json.return_value = {
            "data": {
                "issues": {
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [mock_linear_issue],
                }
            }
        }

        mock_post.side_effect = [viewer_response, page1_response, page2_response]

        provider = LinearProvider()
        provider.api_key = "test-key"
        provider.graphql_url = "https://api.linear.app/graphql"

        items = list(provider.fetch_items(fetch_params_no_user))

        assert len(items) == 2
        assert mock_post.call_count == 3  # viewer + 2 pages

    def test_convert_linear_issue_to_work_item(self, mock_linear_issue):
        """Test converting Linear issue to WorkItem."""
        provider = LinearProvider()

        work_item = provider._convert_linear_issue_to_work_item(mock_linear_issue)

        assert work_item.id == "LIN-123"
        assert work_item.title == "Test Linear Issue"
        assert work_item.description == "Test description"
        assert work_item.url == "https://linear.app/test/issue/LIN-123"
        assert work_item.provider == "Linear"

        # Verify raw_data contains Linear-specific fields
        assert work_item.raw_data["state"]["name"] == "In Progress"
        assert work_item.raw_data["priority"] == 2
        assert work_item.raw_data["priority_label"] == "Medium"
        assert work_item.raw_data["estimate"] == 5
        assert work_item.raw_data["assignee"]["email"] == "test@example.com"
        assert work_item.raw_data["project"]["name"] == "Test Project"
        assert work_item.raw_data["team"]["key"] == "TEST"
        assert work_item.raw_data["cycle"]["number"] == 1
        assert len(work_item.raw_data["labels"]) == 2

    def test_convert_linear_issue_minimal(self):
        """Test converting Linear issue with minimal fields."""
        issue = {
            "id": "minimal-1",
            "identifier": "MIN-1",
            "title": "Minimal issue",
            "description": None,
            "url": "https://linear.app/test/MIN-1",
            "createdAt": "2025-01-01T00:00:00.000Z",
            "updatedAt": "2025-01-01T00:00:00.000Z",
            "archivedAt": None,
            "state": None,
            "priority": None,
            "priorityLabel": None,
            "estimate": None,
            "assignee": None,
            "creator": None,
            "project": None,
            "team": None,
            "cycle": None,
            "labels": None,
            "parent": None,
            "children": None,
            "comments": None,
        }

        provider = LinearProvider()
        work_item = provider._convert_linear_issue_to_work_item(issue)

        assert work_item.id == "MIN-1"
        assert work_item.title == "Minimal issue"
        assert work_item.description == ""
        assert work_item.raw_data["assignee"] is None
        assert work_item.raw_data["state"] is None
        assert work_item.raw_data["estimate"] is None

    def test_convert_linear_issue_with_comments(self, mock_linear_issue):
        """Test converting Linear issue with comments."""
        mock_linear_issue["comments"] = {
            "nodes": [
                {
                    "id": "comment-1",
                    "body": "Test comment",
                    "createdAt": "2025-01-16T10:00:00.000Z",
                    "updatedAt": "2025-01-16T10:00:00.000Z",
                    "user": {
                        "id": "user-1",
                        "name": "commenter",
                        "email": "commenter@example.com",
                        "displayName": "Commenter",
                    },
                }
            ]
        }

        provider = LinearProvider()
        work_item = provider._convert_linear_issue_to_work_item(mock_linear_issue)

        assert work_item.raw_data["comments"]["count"] == 1
        assert work_item.raw_data["comments"]["last_comment_author"] == "Commenter"
        assert len(work_item.raw_data["comments"]["comments"]) == 1

    @patch("src.providers.linear.update_config")
    def test_disconnect(self, mock_update_config):
        """Test disconnecting Linear provider."""
        provider = LinearProvider()
        provider.disconnect()

        mock_update_config.assert_called_once_with("LINEAR_API_KEY", "")

    @patch("src.providers.linear.questionary.password")
    def test_ask_linear_credentials(self, mock_password):
        """Test asking for Linear credentials."""
        from src.providers.linear import ask_linear_credentials

        mock_password.return_value.ask.return_value = "test-linear-key"

        credentials = ask_linear_credentials()

        assert credentials["api_key"] == "test-linear-key"
