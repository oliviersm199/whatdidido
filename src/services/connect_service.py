"""Service for connecting integrations."""

from providers.base import BaseProvider
from service_integrations.base import BaseServiceIntegration


class ConnectResult:
    """Result of a connect operation."""

    def __init__(
        self,
        configured_providers: list[str],
        configured_services: list[str],
        errors: dict[str, str],
    ):
        """Initialize connect result.

        Args:
            configured_providers: List of provider names that were configured
            configured_services: List of service names that were configured
            errors: Dictionary mapping integration names to error messages
        """
        self.configured_providers = configured_providers
        self.configured_services = configured_services
        self.errors = errors
        self.total_configured = len(configured_providers) + len(configured_services)
        self.success = len(errors) == 0


class ConnectService:
    """Handles connecting and setting up data sources and service integrations."""

    def setup_provider(self, provider: BaseProvider) -> tuple[str, str | None]:
        """Set up a single provider.

        Args:
            provider: Provider instance to set up

        Returns:
            Tuple of (provider_name, error_message). error_message is None on success.
        """
        provider_name = provider.get_name()
        try:
            provider.setup()
            return provider_name, None
        except Exception as e:
            return provider_name, str(e)

    def setup_service(self, service: BaseServiceIntegration) -> tuple[str, str | None]:
        """Set up a single service integration.

        Args:
            service: Service instance to set up

        Returns:
            Tuple of (service_name, error_message). error_message is None on success.
        """
        service_name = service.get_name()
        try:
            service.setup()
            return service_name, None
        except Exception as e:
            return service_name, str(e)

    def validate_service(
        self, service: BaseServiceIntegration
    ) -> tuple[str, bool, str | None]:
        """Validate a service integration.

        Args:
            service: Service instance to validate

        Returns:
            Tuple of (service_name, is_valid, error_message)
        """
        service_name = service.get_name()
        try:
            is_valid = service.validate()
            return service_name, is_valid, None
        except Exception as e:
            return service_name, False, str(e)

    def setup_providers(
        self, provider_instances: list[BaseProvider]
    ) -> tuple[list[str], dict[str, str]]:
        """Set up multiple providers.

        Args:
            provider_instances: List of provider instances to set up

        Returns:
            Tuple of (configured_names, errors)
        """
        configured = []
        errors = {}

        for provider in provider_instances:
            name, error = self.setup_provider(provider)
            if error:
                errors[name] = error
            else:
                configured.append(name)

        return configured, errors

    def setup_services(
        self,
        service_instances: list[BaseServiceIntegration],
        validate: bool = False,
    ) -> tuple[list[str], dict[str, str]]:
        """Set up multiple service integrations.

        Args:
            service_instances: List of service instances to set up
            validate: Whether to validate each service after setup

        Returns:
            Tuple of (configured_names, errors)
        """
        configured = []
        errors = {}

        for service in service_instances:
            name, error = self.setup_service(service)
            if error:
                errors[name] = error
                continue

            # Optionally validate
            if validate:
                _, is_valid, val_error = self.validate_service(service)
                if not is_valid:
                    errors[name] = val_error or "Validation failed"
                    continue

            configured.append(name)

        return configured, errors
