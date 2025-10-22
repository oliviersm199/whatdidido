from providers.base import BaseProvider


def get_provider(name: str) -> BaseProvider:
    for provider_cls in BaseProvider.__subclasses__():
        provider = provider_cls()
        if provider.get_name().lower() == name.lower():
            return provider
    raise ValueError(f"Provider with name '{name}' not found.")
