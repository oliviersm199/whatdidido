"""Service for syncing work items from providers."""

from typing import Type

from models.fetch_params import FetchParams
from persist import DataStore
from providers.base import BaseProvider


class SyncResult:
    """Result of syncing a provider."""

    def __init__(self, provider_name: str, count: int, error: str | None = None):
        self.provider_name = provider_name
        self.count = count
        self.error = error
        self.success = error is None


class SyncService:
    """Handles syncing work items from data source providers."""

    def __init__(self, data_store: DataStore | None = None):
        """Initialize the sync service.

        Args:
            data_store: DataStore instance. If None, creates a new one.
        """
        self.data_store = data_store or DataStore()

    def get_authenticated_providers(
        self, provider_classes: list[Type[BaseProvider]]
    ) -> list[BaseProvider]:
        """Get list of authenticated provider instances.

        Args:
            provider_classes: List of provider classes to check

        Returns:
            List of authenticated provider instances
        """
        authenticated = []
        for provider_class in provider_classes:
            instance = provider_class()
            if instance.is_configured() and instance.authenticate():
                authenticated.append(instance)
        return authenticated

    def sync_provider(
        self, provider: BaseProvider, fetch_params: FetchParams
    ) -> SyncResult:
        """Sync work items from a single provider.

        Args:
            provider: Provider instance to sync from
            fetch_params: Parameters for fetching items

        Returns:
            SyncResult with count or error
        """
        provider_name = provider.get_name()

        try:
            count = self.data_store.save_provider_data(provider, fetch_params)
            return SyncResult(provider_name=provider_name, count=count)
        except Exception as e:
            return SyncResult(provider_name=provider_name, count=0, error=str(e))

    def sync_all_providers(
        self, providers: list[BaseProvider], fetch_params: FetchParams
    ) -> list[SyncResult]:
        """Sync work items from multiple providers.

        Args:
            providers: List of provider instances to sync from
            fetch_params: Parameters for fetching items

        Returns:
            List of SyncResult for each provider
        """
        results = []
        for provider in providers:
            result = self.sync_provider(provider, fetch_params)
            results.append(result)
        return results
