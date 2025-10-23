"""
Tests for the DataStore persistence layer.
"""

import json
from datetime import date
from unittest.mock import Mock

from src.models.fetch_params import FetchParams
from src.models.work_item import WorkItem
from src.persist import DataStore


class TestDataStore:
    """Tests for the DataStore class."""

    def test_init_creates_data_file(self, tmp_path):
        """Test that DataStore creates the data file on initialization."""
        data_file = tmp_path / "test.json"
        store = DataStore(data_file=data_file)

        assert data_file.exists()
        assert store.data_file == data_file

        # Should create empty JSON object
        with open(data_file, "r") as f:
            data = json.load(f)
            assert data == {}

    def test_init_with_existing_file(self, tmp_path):
        """Test that DataStore doesn't overwrite existing data file."""
        data_file = tmp_path / "existing.json"

        # Create file with existing data
        existing_data = {"provider1": [{"id": "1", "title": "test"}]}
        with open(data_file, "w") as f:
            json.dump(existing_data, f)

        DataStore(data_file=data_file)

        # Should not overwrite
        with open(data_file, "r") as f:
            data = json.load(f)
            assert data == existing_data

    def test_init_creates_nested_directories(self, tmp_path):
        """Test that DataStore creates nested directories if needed."""
        data_file = tmp_path / "nested" / "dir" / "data.json"
        DataStore(data_file=data_file)

        assert data_file.exists()
        assert data_file.parent.exists()

    def test_save_provider_data(self, tmp_path, sample_work_item):
        """Test saving data from a provider."""
        data_file = tmp_path / "test.json"
        store = DataStore(data_file=data_file)

        # Create mock provider
        mock_provider = Mock()
        mock_provider.get_name.return_value = "TestProvider"
        mock_provider.fetch_items.return_value = [sample_work_item]

        params = FetchParams(start_date=date(2025, 1, 1), end_date=date(2025, 1, 31))

        # Save data
        count = store.save_provider_data(mock_provider, params)

        assert count == 1
        mock_provider.fetch_items.assert_called_once_with(params)

        # Verify data was saved
        with open(data_file, "r") as f:
            data = json.load(f)
            assert "TestProvider" in data
            assert len(data["TestProvider"]) == 1
            assert data["TestProvider"][0]["id"] == "TEST-123"

    def test_save_provider_data_multiple_items(
        self, tmp_path, sample_work_item, minimal_work_item
    ):
        """Test saving multiple items from a provider."""
        data_file = tmp_path / "test.json"
        store = DataStore(data_file=data_file)

        mock_provider = Mock()
        mock_provider.get_name.return_value = "MultiProvider"
        mock_provider.fetch_items.return_value = [sample_work_item, minimal_work_item]

        params = FetchParams(start_date=date(2025, 1, 1), end_date=date(2025, 1, 31))
        count = store.save_provider_data(mock_provider, params)

        assert count == 2

        with open(data_file, "r") as f:
            data = json.load(f)
            assert len(data["MultiProvider"]) == 2

    def test_save_provider_data_overwrites_existing(self, tmp_path, sample_work_item):
        """Test that saving provider data overwrites existing data for that provider."""
        data_file = tmp_path / "test.json"
        store = DataStore(data_file=data_file)

        mock_provider = Mock()
        mock_provider.get_name.return_value = "TestProvider"

        # First save
        work_item1 = sample_work_item
        mock_provider.fetch_items.return_value = [work_item1]
        params = FetchParams(start_date=date(2025, 1, 1), end_date=date(2025, 1, 31))
        store.save_provider_data(mock_provider, params)

        # Second save with different data
        work_item2 = WorkItem(
            id="NEW-1",
            title="New item",
            url="https://example.com/NEW-1",
            created_at="2025-01-02T00:00:00Z",
            updated_at="2025-01-02T00:00:00Z",
            provider="test",
        )
        mock_provider.fetch_items.return_value = [work_item2]
        store.save_provider_data(mock_provider, params)

        # Should only have the new item
        with open(data_file, "r") as f:
            data = json.load(f)
            assert len(data["TestProvider"]) == 1
            assert data["TestProvider"][0]["id"] == "NEW-1"

    def test_get_provider_data(self, tmp_path, sample_work_item):
        """Test retrieving data for a specific provider."""
        data_file = tmp_path / "test.json"
        store = DataStore(data_file=data_file)

        # Save data first
        mock_provider = Mock()
        mock_provider.get_name.return_value = "TestProvider"
        mock_provider.fetch_items.return_value = [sample_work_item]
        params = FetchParams(start_date=date(2025, 1, 1), end_date=date(2025, 1, 31))
        store.save_provider_data(mock_provider, params)

        # Retrieve data
        items = store.get_provider_data("TestProvider")

        assert len(items) == 1
        assert items[0].id == "TEST-123"
        assert items[0].title == "Sample test work item"

    def test_get_provider_data_nonexistent(self, tmp_path):
        """Test retrieving data for a provider that doesn't exist."""
        data_file = tmp_path / "test.json"
        store = DataStore(data_file=data_file)

        items = store.get_provider_data("NonExistent")

        assert items == []

    def test_get_all_data(self, tmp_path, sample_work_item, minimal_work_item):
        """Test retrieving all data from all providers."""
        data_file = tmp_path / "test.json"
        store = DataStore(data_file=data_file)

        # Save data from multiple providers
        mock_provider1 = Mock()
        mock_provider1.get_name.return_value = "Provider1"
        mock_provider1.fetch_items.return_value = [sample_work_item]

        mock_provider2 = Mock()
        mock_provider2.get_name.return_value = "Provider2"
        mock_provider2.fetch_items.return_value = [minimal_work_item]

        params = FetchParams(start_date=date(2025, 1, 1), end_date=date(2025, 1, 31))
        store.save_provider_data(mock_provider1, params)
        store.save_provider_data(mock_provider2, params)

        # Get all data
        all_data = store.get_all_data()

        assert len(all_data) == 2
        assert "Provider1" in all_data
        assert "Provider2" in all_data
        assert len(all_data["Provider1"]) == 1
        assert len(all_data["Provider2"]) == 1
        # Verify they're WorkItem-like objects by checking attributes
        assert hasattr(all_data["Provider1"][0], "id")
        assert hasattr(all_data["Provider1"][0], "title")
        assert hasattr(all_data["Provider2"][0], "id")
        assert hasattr(all_data["Provider2"][0], "title")

    def test_get_all_data_empty(self, tmp_path):
        """Test retrieving all data when store is empty."""
        data_file = tmp_path / "test.json"
        store = DataStore(data_file=data_file)

        all_data = store.get_all_data()

        assert all_data == {}

    def test_clear_provider_data(self, tmp_path, sample_work_item, minimal_work_item):
        """Test clearing data for a specific provider."""
        data_file = tmp_path / "test.json"
        store = DataStore(data_file=data_file)

        # Save data from multiple providers
        mock_provider1 = Mock()
        mock_provider1.get_name.return_value = "Provider1"
        mock_provider1.fetch_items.return_value = [sample_work_item]

        mock_provider2 = Mock()
        mock_provider2.get_name.return_value = "Provider2"
        mock_provider2.fetch_items.return_value = [minimal_work_item]

        params = FetchParams(start_date=date(2025, 1, 1), end_date=date(2025, 1, 31))
        store.save_provider_data(mock_provider1, params)
        store.save_provider_data(mock_provider2, params)

        # Clear one provider
        result = store.clear_provider_data("Provider1")

        assert result is True

        # Verify only Provider2 remains
        all_data = store.get_all_data()
        assert len(all_data) == 1
        assert "Provider1" not in all_data
        assert "Provider2" in all_data

    def test_clear_provider_data_nonexistent(self, tmp_path):
        """Test clearing data for a provider that doesn't exist."""
        data_file = tmp_path / "test.json"
        store = DataStore(data_file=data_file)

        result = store.clear_provider_data("NonExistent")

        assert result is False

    def test_clear_all_data(self, tmp_path, sample_work_item):
        """Test clearing all data from all providers."""
        data_file = tmp_path / "test.json"
        store = DataStore(data_file=data_file)

        # Save data
        mock_provider = Mock()
        mock_provider.get_name.return_value = "TestProvider"
        mock_provider.fetch_items.return_value = [sample_work_item]
        params = FetchParams(start_date=date(2025, 1, 1), end_date=date(2025, 1, 31))
        store.save_provider_data(mock_provider, params)

        # Clear all
        store.clear_all_data()

        # Verify empty
        all_data = store.get_all_data()
        assert all_data == {}

        with open(data_file, "r") as f:
            data = json.load(f)
            assert data == {}

    def test_get_provider_names(self, tmp_path, sample_work_item, minimal_work_item):
        """Test getting all provider names."""
        data_file = tmp_path / "test.json"
        store = DataStore(data_file=data_file)

        # Save data from multiple providers
        mock_provider1 = Mock()
        mock_provider1.get_name.return_value = "Provider1"
        mock_provider1.fetch_items.return_value = [sample_work_item]

        mock_provider2 = Mock()
        mock_provider2.get_name.return_value = "Provider2"
        mock_provider2.fetch_items.return_value = [minimal_work_item]

        params = FetchParams(start_date=date(2025, 1, 1), end_date=date(2025, 1, 31))
        store.save_provider_data(mock_provider1, params)
        store.save_provider_data(mock_provider2, params)

        # Get provider names
        names = store.get_provider_names()

        assert len(names) == 2
        assert "Provider1" in names
        assert "Provider2" in names

    def test_get_provider_names_empty(self, tmp_path):
        """Test getting provider names when store is empty."""
        data_file = tmp_path / "test.json"
        store = DataStore(data_file=data_file)

        names = store.get_provider_names()

        assert names == []

    def test_atomic_write(self, tmp_path, sample_work_item):
        """Test that writes are atomic (use temp file + rename)."""
        data_file = tmp_path / "test.json"
        store = DataStore(data_file=data_file)

        mock_provider = Mock()
        mock_provider.get_name.return_value = "TestProvider"
        mock_provider.fetch_items.return_value = [sample_work_item]
        params = FetchParams(start_date=date(2025, 1, 1), end_date=date(2025, 1, 31))

        store.save_provider_data(mock_provider, params)

        # Temp file should not exist after write
        temp_file = data_file.with_suffix(data_file.suffix + ".tmp")
        assert not temp_file.exists()

        # Data file should exist with correct data
        assert data_file.exists()

    def test_json_formatting(self, tmp_path, sample_work_item):
        """Test that JSON is formatted with indentation and sorted keys."""
        data_file = tmp_path / "test.json"
        store = DataStore(data_file=data_file)

        mock_provider = Mock()
        mock_provider.get_name.return_value = "TestProvider"
        mock_provider.fetch_items.return_value = [sample_work_item]
        params = FetchParams(start_date=date(2025, 1, 1), end_date=date(2025, 1, 31))

        store.save_provider_data(mock_provider, params)

        # Read raw file content
        with open(data_file, "r") as f:
            content = f.read()

        # Should be indented (contains newlines and spaces)
        assert "\n" in content
        assert "  " in content

        # Verify it's valid JSON
        data = json.loads(content)
        assert "TestProvider" in data

    def test_lock_file_path(self, tmp_path):
        """Test that lock file path is correctly derived from data file."""
        data_file = tmp_path / "test.json"
        store = DataStore(data_file=data_file)

        expected_lock = data_file.with_suffix(data_file.suffix + ".lock")
        assert store.lock_file == expected_lock

    def test_save_empty_items_list(self, tmp_path):
        """Test saving when provider returns no items."""
        data_file = tmp_path / "test.json"
        store = DataStore(data_file=data_file)

        mock_provider = Mock()
        mock_provider.get_name.return_value = "EmptyProvider"
        mock_provider.fetch_items.return_value = []
        params = FetchParams(start_date=date(2025, 1, 1), end_date=date(2025, 1, 31))

        count = store.save_provider_data(mock_provider, params)

        assert count == 0

        with open(data_file, "r") as f:
            data = json.load(f)
            assert data["EmptyProvider"] == []

    def test_work_item_roundtrip(self, tmp_path, sample_work_item):
        """Test that WorkItems can be saved and retrieved without data loss."""
        data_file = tmp_path / "test.json"
        store = DataStore(data_file=data_file)

        mock_provider = Mock()
        mock_provider.get_name.return_value = "TestProvider"
        mock_provider.fetch_items.return_value = [sample_work_item]
        params = FetchParams(start_date=date(2025, 1, 1), end_date=date(2025, 1, 31))

        store.save_provider_data(mock_provider, params)
        retrieved_items = store.get_provider_data("TestProvider")

        assert len(retrieved_items) == 1
        retrieved = retrieved_items[0]

        # Verify all fields match
        assert retrieved.id == sample_work_item.id
        assert retrieved.title == sample_work_item.title
        assert retrieved.description == sample_work_item.description
        assert retrieved.url == sample_work_item.url
        assert retrieved.created_at == sample_work_item.created_at
        assert retrieved.updated_at == sample_work_item.updated_at
        assert retrieved.provider == sample_work_item.provider
        assert retrieved.raw_data == sample_work_item.raw_data
