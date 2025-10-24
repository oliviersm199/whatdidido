"""Tests for the SyncService."""

from unittest.mock import Mock

from src.services.sync_service import SyncService, SyncResult


class TestSyncResult:
    """Tests for SyncResult class."""

    def test_sync_result_success(self):
        """Test creating a successful SyncResult."""
        result = SyncResult(provider_name="Jira", count=10)

        assert result.provider_name == "Jira"
        assert result.count == 10
        assert result.error is None
        assert result.success is True

    def test_sync_result_failure(self):
        """Test creating a failed SyncResult."""
        result = SyncResult(provider_name="Jira", count=0, error="Connection failed")

        assert result.provider_name == "Jira"
        assert result.count == 0
        assert result.error == "Connection failed"
        assert result.success is False


class TestSyncService:
    """Tests for SyncService class."""

    def test_init_default(self):
        """Test initialization with default DataStore."""
        service = SyncService()

        assert service.data_store is not None

    def test_init_with_data_store(self):
        """Test initialization with custom DataStore."""
        mock_store = Mock()
        service = SyncService(data_store=mock_store)

        assert service.data_store is mock_store

    def test_get_authenticated_providers_all_authenticated(self):
        """Test getting authenticated providers when all are configured."""
        # Create mock provider classes
        mock_provider_class1 = Mock()
        mock_instance1 = Mock()
        mock_instance1.is_configured.return_value = True
        mock_instance1.authenticate.return_value = True
        mock_provider_class1.return_value = mock_instance1

        mock_provider_class2 = Mock()
        mock_instance2 = Mock()
        mock_instance2.is_configured.return_value = True
        mock_instance2.authenticate.return_value = True
        mock_provider_class2.return_value = mock_instance2

        service = SyncService()
        providers = service.get_authenticated_providers(
            [mock_provider_class1, mock_provider_class2]
        )

        assert len(providers) == 2
        assert providers[0] is mock_instance1
        assert providers[1] is mock_instance2

    def test_get_authenticated_providers_some_not_configured(self):
        """Test getting authenticated providers when some are not configured."""
        mock_provider_class1 = Mock()
        mock_instance1 = Mock()
        mock_instance1.is_configured.return_value = False
        mock_provider_class1.return_value = mock_instance1

        mock_provider_class2 = Mock()
        mock_instance2 = Mock()
        mock_instance2.is_configured.return_value = True
        mock_instance2.authenticate.return_value = True
        mock_provider_class2.return_value = mock_instance2

        service = SyncService()
        providers = service.get_authenticated_providers(
            [mock_provider_class1, mock_provider_class2]
        )

        assert len(providers) == 1
        assert providers[0] is mock_instance2

    def test_get_authenticated_providers_authentication_fails(self):
        """Test getting authenticated providers when authentication fails."""
        mock_provider_class = Mock()
        mock_instance = Mock()
        mock_instance.is_configured.return_value = True
        mock_instance.authenticate.return_value = False
        mock_provider_class.return_value = mock_instance

        service = SyncService()
        providers = service.get_authenticated_providers([mock_provider_class])

        assert len(providers) == 0

    def test_get_authenticated_providers_empty_list(self):
        """Test getting authenticated providers with empty list."""
        service = SyncService()
        providers = service.get_authenticated_providers([])

        assert len(providers) == 0

    def test_sync_provider_success(self, sample_fetch_params):
        """Test syncing from a single provider successfully."""
        mock_store = Mock()
        mock_store.save_provider_data.return_value = 5

        mock_provider = Mock()
        mock_provider.get_name.return_value = "Jira"

        service = SyncService(data_store=mock_store)
        result = service.sync_provider(mock_provider, sample_fetch_params)

        assert result.success is True
        assert result.provider_name == "Jira"
        assert result.count == 5
        assert result.error is None

        mock_store.save_provider_data.assert_called_once_with(
            mock_provider, sample_fetch_params
        )

    def test_sync_provider_failure(self, sample_fetch_params):
        """Test syncing from a provider that fails."""
        mock_store = Mock()
        mock_store.save_provider_data.side_effect = Exception("Network error")

        mock_provider = Mock()
        mock_provider.get_name.return_value = "Jira"

        service = SyncService(data_store=mock_store)
        result = service.sync_provider(mock_provider, sample_fetch_params)

        assert result.success is False
        assert result.provider_name == "Jira"
        assert result.count == 0
        assert result.error == "Network error"

    def test_sync_all_providers_success(self, sample_fetch_params):
        """Test syncing from multiple providers successfully."""
        mock_store = Mock()
        mock_store.save_provider_data.side_effect = [5, 10]

        mock_provider1 = Mock()
        mock_provider1.get_name.return_value = "Jira"

        mock_provider2 = Mock()
        mock_provider2.get_name.return_value = "Linear"

        service = SyncService(data_store=mock_store)
        results = service.sync_all_providers(
            [mock_provider1, mock_provider2], sample_fetch_params
        )

        assert len(results) == 2
        assert results[0].provider_name == "Jira"
        assert results[0].count == 5
        assert results[0].success is True
        assert results[1].provider_name == "Linear"
        assert results[1].count == 10
        assert results[1].success is True

    def test_sync_all_providers_mixed_results(self, sample_fetch_params):
        """Test syncing from multiple providers with mixed success/failure."""
        mock_store = Mock()
        mock_store.save_provider_data.side_effect = [5, Exception("API error")]

        mock_provider1 = Mock()
        mock_provider1.get_name.return_value = "Jira"

        mock_provider2 = Mock()
        mock_provider2.get_name.return_value = "Linear"

        service = SyncService(data_store=mock_store)
        results = service.sync_all_providers(
            [mock_provider1, mock_provider2], sample_fetch_params
        )

        assert len(results) == 2
        assert results[0].success is True
        assert results[0].count == 5
        assert results[1].success is False
        assert results[1].error == "API error"

    def test_sync_all_providers_empty_list(self, sample_fetch_params):
        """Test syncing with empty provider list."""
        service = SyncService()
        results = service.sync_all_providers([], sample_fetch_params)

        assert len(results) == 0
