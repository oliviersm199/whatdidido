"""
Shared pytest fixtures for the test suite.
"""

from datetime import date

import pytest

from src.models.fetch_params import FetchParams
from src.models.work_item import WorkItem


@pytest.fixture
def sample_work_item():
    """Create a sample WorkItem for testing."""
    return WorkItem(
        id="TEST-123",
        title="Sample test work item",
        description="This is a test work item description",
        url="https://example.com/issues/TEST-123",
        created_at="2025-01-15T10:00:00Z",
        updated_at="2025-01-20T15:30:00Z",
        provider="jira",
        raw_data={
            "status": "In Progress",
            "assignee": "user@example.com",
            "labels": ["bug", "urgent"],
        },
    )


@pytest.fixture
def minimal_work_item():
    """Create a minimal WorkItem with only required fields."""
    return WorkItem(
        id="MIN-1",
        title="Minimal item",
        url="https://example.com/MIN-1",
        created_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z",
        provider="test",
    )


@pytest.fixture
def sample_fetch_params():
    """Create sample FetchParams for testing."""
    return FetchParams(
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 31),
        user_filter="user@example.com",
    )


@pytest.fixture
def fetch_params_no_user():
    """Create FetchParams without user filter."""
    return FetchParams(
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 31),
    )


@pytest.fixture
def mock_jira_config():
    """Create a mock configuration for Jira."""
    from unittest.mock import Mock

    config = Mock()
    config.jira.jira_url = "https://test.atlassian.net"
    config.jira.jira_username = "test@example.com"
    config.jira.jira_api_key = "test-api-key"
    return config


@pytest.fixture
def mock_linear_config():
    """Create a mock configuration for Linear."""
    from unittest.mock import Mock

    config = Mock()
    config.linear.linear_api_key = "test-linear-api-key"
    return config


@pytest.fixture
def mock_jira_issue():
    """Create a mock Jira issue object."""
    from unittest.mock import Mock

    issue = Mock()
    issue.key = "TEST-123"
    issue.fields = Mock()
    issue.fields.summary = "Test Jira Issue"
    issue.fields.description = "Test description"
    issue.fields.created = "2025-01-15T10:00:00.000+0000"
    issue.fields.updated = "2025-01-20T15:30:00.000+0000"
    issue.fields.status = Mock()
    issue.fields.status.name = "In Progress"
    issue.fields.status.statusCategory = Mock()
    issue.fields.status.statusCategory.name = "In Progress"
    issue.fields.issuetype = Mock()
    issue.fields.issuetype.name = "Task"
    issue.fields.priority = Mock()
    issue.fields.priority.name = "Medium"
    issue.fields.assignee = Mock()
    issue.fields.assignee.displayName = "Test User"
    issue.fields.assignee.name = "testuser"
    issue.fields.assignee.emailAddress = "test@example.com"
    issue.fields.reporter = Mock()
    issue.fields.reporter.displayName = "Reporter User"
    issue.fields.reporter.name = "reporter"
    issue.fields.reporter.emailAddress = "reporter@example.com"
    issue.fields.creator = Mock()
    issue.fields.creator.displayName = "Creator User"
    issue.fields.creator.name = "creator"
    issue.fields.creator.emailAddress = "creator@example.com"
    issue.fields.project = Mock()
    issue.fields.project.key = "TEST"
    issue.fields.project.name = "Test Project"
    issue.fields.labels = ["bug", "urgent"]
    issue.fields.components = []
    issue.fields.subtasks = []
    issue.fields.parent = None
    issue.fields.comment = Mock()
    issue.fields.comment.comments = []
    issue.fields.resolution = None
    issue.fields.resolutiondate = None
    issue.fields.environment = None
    issue.fields.timetracking = None
    return issue


@pytest.fixture
def mock_linear_issue():
    """Create a mock Linear issue object."""
    return {
        "id": "linear-123",
        "identifier": "LIN-123",
        "title": "Test Linear Issue",
        "description": "Test description",
        "url": "https://linear.app/test/issue/LIN-123",
        "createdAt": "2025-01-15T10:00:00.000Z",
        "updatedAt": "2025-01-20T15:30:00.000Z",
        "archivedAt": None,
        "state": {
            "id": "state-1",
            "name": "In Progress",
            "type": "started",
            "color": "#f2c94c",
        },
        "priority": 2,
        "priorityLabel": "Medium",
        "estimate": 5,
        "assignee": {
            "id": "user-1",
            "name": "testuser",
            "email": "test@example.com",
            "displayName": "Test User",
        },
        "creator": {
            "id": "user-2",
            "name": "creator",
            "email": "creator@example.com",
            "displayName": "Creator User",
        },
        "project": {
            "id": "project-1",
            "name": "Test Project",
            "description": "Test project description",
            "state": "started",
            "targetDate": "2025-02-01",
        },
        "team": {
            "id": "team-1",
            "name": "Test Team",
            "key": "TEST",
        },
        "cycle": {
            "id": "cycle-1",
            "number": 1,
            "name": "Cycle 1",
            "startsAt": "2025-01-01T00:00:00.000Z",
            "endsAt": "2025-01-14T23:59:59.000Z",
        },
        "labels": {
            "nodes": [
                {"id": "label-1", "name": "bug", "color": "#ff0000"},
                {"id": "label-2", "name": "urgent", "color": "#ff6600"},
            ]
        },
        "parent": None,
        "children": {"nodes": []},
        "comments": {"nodes": []},
    }
