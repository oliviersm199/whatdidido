"""
Persist raw data synced from third parties into JSON files
"""

import json
from pathlib import Path
from typing import Any

from filelock import FileLock

from models.fetch_params import FetchParams
from models.work_item import WorkItem
from providers.base import BaseProvider
from utils.lock_utils import with_lock_cleanup

FILE_NAME = "whatdidido.json"
LOCK_NAME = "whatdidido.json.lock"  # Lock file without leading dot


class DataStore:
    """
    Handles persistence of work items from various providers to a JSON file.

    The data is stored in the format:
    {
        "provider_name": [
            {"id": "...", "title": "...", ...},
            ...
        ]
    }
    """

    def __init__(self, data_file: Path | None = None):
        """
        Initialize the DataStore.

        Args:
            data_file: Path to the JSON file. If None, uses default location.
        """
        self.data_file = data_file or Path(FILE_NAME)
        self.lock_file = self.data_file.with_suffix(self.data_file.suffix + ".lock")
        self._ensure_data_file_exists()

    def _ensure_data_file_exists(self) -> None:
        """Create the data file with empty structure if it doesn't exist."""
        if not self.data_file.exists():
            self.data_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.data_file, "w") as f:
                json.dump({}, f)

    def _get_lock(self) -> FileLock:
        """Get a file lock for thread-safe operations."""
        return FileLock(str(self.lock_file), timeout=10)

    def _read_all_data(self) -> dict[str, list[dict[str, Any]]]:
        """Read all data from the JSON file (internal method, assumes lock is held)."""
        with open(self.data_file, "r") as f:
            return json.load(f)

    def _write_all_data(self, data: dict[str, list[dict[str, Any]]]) -> None:
        """
        Write all data to the JSON file atomically.

        Uses atomic write pattern: write to temp file, then rename.
        This ensures data integrity even if the process is interrupted.
        """
        temp_file = self.data_file.with_suffix(self.data_file.suffix + ".tmp")
        with open(temp_file, "w") as f:
            json.dump(data, f, indent=2, sort_keys=True)
        temp_file.replace(self.data_file)

    def save_provider_data(self, provider: BaseProvider, params: FetchParams) -> int:
        """
        Fetch and save work items from a provider.

        Args:
            provider: The provider to fetch data from
            params: FetchParams object containing filtering options

        Returns:
            Number of items saved

        Example:
            store = DataStore()
            jira_provider = JiraProvider()
            params = FetchParams(start_date=date(2024, 1, 1), end_date=date(2024, 1, 31))
            count = store.save_provider_data(jira_provider, params)
        """
        provider_name = provider.get_name()
        items: list[dict[str, Any]] = []

        # Fetch items from provider
        for work_item in provider.fetch_items(params):
            items.append(work_item.model_dump())

        # Save to file with lock
        self._save_items(provider_name, items)

        return len(items)

    @with_lock_cleanup(LOCK_NAME)
    def _save_items(self, provider_name: str, items: list[dict[str, Any]]) -> None:
        """Internal method to save items with lock cleanup."""
        data = self._read_all_data()
        data[provider_name] = items
        self._write_all_data(data)

    @with_lock_cleanup(LOCK_NAME)
    def get_provider_data(self, provider_name: str) -> list[WorkItem]:
        """
        Get all work items for a specific provider.

        Args:
            provider_name: Name of the provider

        Returns:
            List of WorkItem objects

        Example:
            store = DataStore()
            jira_items = store.get_provider_data("Jira")
        """
        data = self._read_all_data()
        items_data = data.get(provider_name, [])
        return [WorkItem(**item) for item in items_data]

    @with_lock_cleanup(LOCK_NAME)
    def get_all_data(self) -> dict[str, list[WorkItem]]:
        """
        Get all work items from all providers.

        Returns:
            Dictionary mapping provider names to lists of WorkItem objects

        Example:
            store = DataStore()
            all_items = store.get_all_data()
            for provider, items in all_items.items():
                print(f"{provider}: {len(items)} items")
        """
        data = self._read_all_data()
        return {
            provider_name: [WorkItem(**item) for item in items]
            for provider_name, items in data.items()
        }

    @with_lock_cleanup(LOCK_NAME)
    def clear_provider_data(self, provider_name: str) -> bool:
        """
        Clear all data for a specific provider.

        Args:
            provider_name: Name of the provider to clear

        Returns:
            True if data was cleared, False if provider had no data

        Example:
            store = DataStore()
            cleared = store.clear_provider_data("Jira")
        """
        data = self._read_all_data()
        if provider_name in data:
            del data[provider_name]
            self._write_all_data(data)
            return True
        return False

    @with_lock_cleanup(LOCK_NAME)
    def clear_all_data(self) -> None:
        """
        Clear all data from all providers.

        Example:
            store = DataStore()
            store.clear_all_data()
        """
        self._write_all_data({})

    @with_lock_cleanup(LOCK_NAME)
    def get_provider_names(self) -> list[str]:
        """
        Get names of all providers that have data stored.

        Returns:
            List of provider names

        Example:
            store = DataStore()
            providers = store.get_provider_names()
        """
        data = self._read_all_data()
        return list(data.keys())
