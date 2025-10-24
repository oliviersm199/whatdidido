"""Service for disconnecting integrations."""

from typing import Sequence, Type

from providers.base import BaseProvider
from service_integrations.base import BaseServiceIntegration


class DisconnectResult:
    """Result of a disconnect operation."""

    def __init__(
        self,
        disconnected_providers: list[str],
        disconnected_services: list[str],
        errors: dict[str, str],
    ):
        """Initialize disconnect result.

        Args:
            disconnected_providers: List of provider names that were disconnected
            disconnected_services: List of service names that were disconnected
            errors: Dictionary mapping integration names to error messages
        """
        self.disconnected_providers = disconnected_providers
        self.disconnected_services = disconnected_services
        self.errors = errors
        self.total_disconnected = len(disconnected_providers) + len(
            disconnected_services
        )
        self.success = len(errors) == 0


class DisconnectService:
    """Handles disconnecting data sources and service integrations."""

    def get_configured_providers(
        self, provider_classes: Sequence[Type[BaseProvider]]
    ) -> list[BaseProvider]:
        """Get list of configured provider instances.

        Args:
            provider_classes: List of provider classes to check

        Returns:
            List of configured provider instances
        """
        configured = []
        for provider_class in provider_classes:
            instance = provider_class()
            if instance.is_configured():
                configured.append(instance)
        return configured

    def get_configured_services(
        self, service_classes: Sequence[Type[BaseServiceIntegration]]
    ) -> list[BaseServiceIntegration]:
        """Get list of configured service instances.

        Args:
            service_classes: List of service classes to check

        Returns:
            List of configured service instances
        """
        configured = []
        for service_class in service_classes:
            instance = service_class()
            if instance.is_configured():
                configured.append(instance)
        return configured

    def disconnect_providers(
        self, providers: list[BaseProvider]
    ) -> tuple[list[str], dict[str, str]]:
        """Disconnect a list of providers.

        Args:
            providers: List of provider instances to disconnect

        Returns:
            Tuple of (disconnected_names, errors)
        """
        disconnected = []
        errors = {}

        for provider in providers:
            provider_name = provider.get_name()
            try:
                provider.disconnect()
                disconnected.append(provider_name)
            except Exception as e:
                errors[provider_name] = str(e)

        return disconnected, errors

    def disconnect_services(
        self, services: list[BaseServiceIntegration]
    ) -> tuple[list[str], dict[str, str]]:
        """Disconnect a list of services.

        Args:
            services: List of service instances to disconnect

        Returns:
            Tuple of (disconnected_names, errors)
        """
        disconnected = []
        errors = {}

        for service in services:
            service_name = service.get_name()
            try:
                service.disconnect()
                disconnected.append(service_name)
            except Exception as e:
                errors[service_name] = str(e)

        return disconnected, errors

    def disconnect_all(
        self,
        provider_classes: Sequence[Type[BaseProvider]] | None = None,
        service_classes: Sequence[Type[BaseServiceIntegration]] | None = None,
    ) -> DisconnectResult:
        """Disconnect all configured providers and services.

        Args:
            provider_classes: List of provider classes to disconnect
            service_classes: List of service classes to disconnect

        Returns:
            DisconnectResult with lists of disconnected integrations and errors
        """
        disconnected_providers: list[str] = []
        disconnected_services: list[str] = []
        all_errors: dict[str, str] = {}

        # Disconnect providers
        if provider_classes:
            providers = self.get_configured_providers(provider_classes)
            disconnected_providers, provider_errors = self.disconnect_providers(
                providers
            )
            all_errors.update(provider_errors)

        # Disconnect services
        if service_classes:
            services = self.get_configured_services(service_classes)
            disconnected_services, service_errors = self.disconnect_services(services)
            all_errors.update(service_errors)

        return DisconnectResult(
            disconnected_providers=disconnected_providers,
            disconnected_services=disconnected_services,
            errors=all_errors,
        )
