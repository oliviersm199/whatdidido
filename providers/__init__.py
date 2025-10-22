from inspect import isabstract

from providers.base import BaseProvider


def get_provider(name: str) -> BaseProvider:
    for provider_cls in BaseProvider.__subclasses__():
        if isabstract(provider_cls):
            continue
        provider = provider_cls()  # type: ignore[abstract]
        if provider.get_name().lower() == name.lower():
            return provider
    raise ValueError(f"Provider with name '{name}' not found.")
