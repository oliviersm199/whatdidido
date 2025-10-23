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
