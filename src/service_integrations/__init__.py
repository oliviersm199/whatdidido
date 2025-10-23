"""Service integrations package for AI, notifications, and other services."""

from inspect import isabstract

from service_integrations.base import BaseServiceIntegration


def get_service_integration(name: str) -> BaseServiceIntegration:
    """Get a service integration instance by name.

    Args:
        name: The name of the service integration (case-insensitive).

    Returns:
        An instance of the requested service integration.

    Raises:
        ValueError: If no service integration with the given name is found.
    """
    for service_cls in BaseServiceIntegration.__subclasses__():
        if isabstract(service_cls):
            continue
        # Type narrowing: at this point we know service_cls is not abstract
        service = service_cls()  # type: ignore[abstract]
        if service.get_name().lower() == name.lower():
            return service
    raise ValueError(f"Service integration with name '{name}' not found.")


__all__ = ["BaseServiceIntegration", "get_service_integration"]
