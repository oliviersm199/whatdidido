"""Base class for service integrations (AI, notifications, etc.)."""

from abc import ABC, abstractmethod


class BaseServiceIntegration(ABC):
    """Base class for service integrations that provide additional functionality.

    Service integrations are different from data source providers:
    - They do NOT fetch work items or activities
    - They provide services like AI summarization, notifications, etc.
    - They are configured during init but not used in sync operations
    """

    @abstractmethod
    def get_name(self) -> str:
        """Get the name of the service integration."""

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if service integration has required configuration."""

    @abstractmethod
    def setup(self) -> None:
        """Implement setup logic (ask for credentials, API keys, etc)."""

    @abstractmethod
    def validate(self) -> bool:
        """Validate configuration and connection with the service.

        Returns:
            True if validation succeeds, False otherwise.
        """

    @abstractmethod
    def disconnect(self) -> None:
        """Remove all configuration for this service (credentials, settings, etc.)"""
