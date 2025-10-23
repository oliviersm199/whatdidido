"""
Tests for data models: WorkItem and FetchParams.
"""

from datetime import date

import pytest
from pydantic import ValidationError

from src.models.fetch_params import FetchParams
from src.models.work_item import WorkItem


class TestWorkItem:
    """Tests for the WorkItem model."""

    def test_create_work_item_with_all_fields(self, sample_work_item):
        """Test creating a WorkItem with all fields populated."""
        assert sample_work_item.id == "TEST-123"
        assert sample_work_item.title == "Sample test work item"
        assert sample_work_item.description == "This is a test work item description"
        assert sample_work_item.url == "https://example.com/issues/TEST-123"
        assert sample_work_item.created_at == "2025-01-15T10:00:00Z"
        assert sample_work_item.updated_at == "2025-01-20T15:30:00Z"
        assert sample_work_item.provider == "jira"
        assert sample_work_item.raw_data == {
            "status": "In Progress",
            "assignee": "user@example.com",
            "labels": ["bug", "urgent"],
        }

    def test_create_minimal_work_item(self, minimal_work_item):
        """Test creating a WorkItem with only required fields."""
        assert minimal_work_item.id == "MIN-1"
        assert minimal_work_item.title == "Minimal item"
        assert minimal_work_item.description is None
        assert minimal_work_item.url == "https://example.com/MIN-1"
        assert minimal_work_item.created_at == "2025-01-01T00:00:00Z"
        assert minimal_work_item.updated_at == "2025-01-01T00:00:00Z"
        assert minimal_work_item.provider == "test"
        assert minimal_work_item.raw_data == {}

    def test_work_item_missing_required_field_id(self):
        """Test that WorkItem fails validation without id."""
        with pytest.raises(ValidationError) as exc_info:
            WorkItem(
                title="Test",
                url="https://example.com",
                created_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z",
                provider="test",
            )
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("id",) for error in errors)

    def test_work_item_missing_required_field_title(self):
        """Test that WorkItem fails validation without title."""
        with pytest.raises(ValidationError) as exc_info:
            WorkItem(
                id="TEST-1",
                url="https://example.com",
                created_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z",
                provider="test",
            )
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("title",) for error in errors)

    def test_work_item_missing_required_field_url(self):
        """Test that WorkItem fails validation without url."""
        with pytest.raises(ValidationError) as exc_info:
            WorkItem(
                id="TEST-1",
                title="Test",
                created_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z",
                provider="test",
            )
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("url",) for error in errors)

    def test_work_item_missing_required_field_created_at(self):
        """Test that WorkItem fails validation without created_at."""
        with pytest.raises(ValidationError) as exc_info:
            WorkItem(
                id="TEST-1",
                title="Test",
                url="https://example.com",
                updated_at="2025-01-01T00:00:00Z",
                provider="test",
            )
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("created_at",) for error in errors)

    def test_work_item_missing_required_field_updated_at(self):
        """Test that WorkItem fails validation without updated_at."""
        with pytest.raises(ValidationError) as exc_info:
            WorkItem(
                id="TEST-1",
                title="Test",
                url="https://example.com",
                created_at="2025-01-01T00:00:00Z",
                provider="test",
            )
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("updated_at",) for error in errors)

    def test_work_item_missing_required_field_provider(self):
        """Test that WorkItem fails validation without provider."""
        with pytest.raises(ValidationError) as exc_info:
            WorkItem(
                id="TEST-1",
                title="Test",
                url="https://example.com",
                created_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z",
            )
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("provider",) for error in errors)

    def test_work_item_serialization(self, sample_work_item):
        """Test that WorkItem can be serialized to dict."""
        data = sample_work_item.model_dump()
        assert isinstance(data, dict)
        assert data["id"] == "TEST-123"
        assert data["title"] == "Sample test work item"
        assert data["provider"] == "jira"
        assert "raw_data" in data

    def test_work_item_deserialization(self):
        """Test that WorkItem can be deserialized from dict."""
        data = {
            "id": "DESER-1",
            "title": "Deserialized item",
            "url": "https://example.com/DESER-1",
            "created_at": "2025-01-10T12:00:00Z",
            "updated_at": "2025-01-10T12:00:00Z",
            "provider": "linear",
            "raw_data": {"custom_field": "value"},
        }
        item = WorkItem(**data)
        assert item.id == "DESER-1"
        assert item.title == "Deserialized item"
        assert item.provider == "linear"
        assert item.raw_data["custom_field"] == "value"

    def test_work_item_with_empty_description(self):
        """Test WorkItem with None description (optional field)."""
        item = WorkItem(
            id="TEST-2",
            title="No description",
            description=None,
            url="https://example.com",
            created_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
            provider="test",
        )
        assert item.description is None

    def test_work_item_with_empty_raw_data(self):
        """Test WorkItem with empty raw_data (defaults to empty dict)."""
        item = WorkItem(
            id="TEST-3",
            title="No raw data",
            url="https://example.com",
            created_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
            provider="test",
        )
        assert item.raw_data == {}

    def test_work_item_raw_data_with_nested_structures(self):
        """Test WorkItem with complex nested raw_data."""
        item = WorkItem(
            id="TEST-4",
            title="Complex data",
            url="https://example.com",
            created_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
            provider="jira",
            raw_data={
                "status": {"name": "In Progress", "id": 3},
                "assignee": {"email": "user@example.com", "name": "User"},
                "custom_fields": [
                    {"id": "field1", "value": "val1"},
                    {"id": "field2", "value": "val2"},
                ],
            },
        )
        assert item.raw_data["status"]["name"] == "In Progress"
        assert len(item.raw_data["custom_fields"]) == 2

    def test_work_item_different_providers(self):
        """Test WorkItem with different provider types."""
        providers = ["jira", "linear", "github", "custom"]
        for provider in providers:
            item = WorkItem(
                id=f"{provider.upper()}-1",
                title=f"Item from {provider}",
                url=f"https://{provider}.example.com/1",
                created_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z",
                provider=provider,
            )
            assert item.provider == provider


class TestFetchParams:
    """Tests for the FetchParams model."""

    def test_create_fetch_params_with_user_filter(self, sample_fetch_params):
        """Test creating FetchParams with all fields."""
        assert sample_fetch_params.start_date == date(2025, 1, 1)
        assert sample_fetch_params.end_date == date(2025, 1, 31)
        assert sample_fetch_params.user_filter == "user@example.com"

    def test_create_fetch_params_without_user_filter(self, fetch_params_no_user):
        """Test creating FetchParams without user_filter (optional)."""
        assert fetch_params_no_user.start_date == date(2025, 1, 1)
        assert fetch_params_no_user.end_date == date(2025, 1, 31)
        assert fetch_params_no_user.user_filter is None

    def test_fetch_params_missing_start_date(self):
        """Test that FetchParams fails validation without start_date."""
        with pytest.raises(ValidationError) as exc_info:
            FetchParams(
                end_date=date(2025, 1, 31),
            )
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("start_date",) for error in errors)

    def test_fetch_params_missing_end_date(self):
        """Test that FetchParams fails validation without end_date."""
        with pytest.raises(ValidationError) as exc_info:
            FetchParams(
                start_date=date(2025, 1, 1),
            )
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("end_date",) for error in errors)

    def test_fetch_params_date_validation(self):
        """Test FetchParams with valid date objects."""
        params = FetchParams(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
        )
        assert params.start_date.year == 2025
        assert params.start_date.month == 1
        assert params.end_date.month == 12

    def test_fetch_params_serialization(self, sample_fetch_params):
        """Test that FetchParams can be serialized to dict."""
        data = sample_fetch_params.model_dump()
        assert isinstance(data, dict)
        assert data["start_date"] == date(2025, 1, 1)
        assert data["end_date"] == date(2025, 1, 31)
        assert data["user_filter"] == "user@example.com"

    def test_fetch_params_deserialization(self):
        """Test that FetchParams can be deserialized from dict."""
        data = {
            "start_date": date(2025, 2, 1),
            "end_date": date(2025, 2, 28),
            "user_filter": "admin@example.com",
        }
        params = FetchParams(**data)
        assert params.start_date == date(2025, 2, 1)
        assert params.end_date == date(2025, 2, 28)
        assert params.user_filter == "admin@example.com"

    def test_fetch_params_with_date_range(self):
        """Test FetchParams with various date ranges."""
        # Single day
        params1 = FetchParams(
            start_date=date(2025, 1, 15),
            end_date=date(2025, 1, 15),
        )
        assert params1.start_date == params1.end_date

        # Full year
        params2 = FetchParams(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
        )
        assert (params2.end_date - params2.start_date).days == 364

    def test_fetch_params_user_filter_variations(self):
        """Test FetchParams with different user_filter formats."""
        # Email format
        params1 = FetchParams(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            user_filter="user@example.com",
        )
        assert params1.user_filter == "user@example.com"

        # Username format
        params2 = FetchParams(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            user_filter="username123",
        )
        assert params2.user_filter == "username123"

        # ID format
        params3 = FetchParams(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            user_filter="507f1f77bcf86cd799439011",
        )
        assert params3.user_filter == "507f1f77bcf86cd799439011"

    def test_fetch_params_json_serialization(self, sample_fetch_params):
        """Test that FetchParams can be serialized to JSON-compatible format."""
        json_data = sample_fetch_params.model_dump(mode="json")
        assert isinstance(json_data, dict)
        # Dates should be serialized as strings in JSON mode
        assert isinstance(json_data["start_date"], str) or isinstance(
            json_data["start_date"], date
        )
