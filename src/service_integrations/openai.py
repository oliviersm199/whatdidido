"""OpenAI service integration for AI-powered summarization."""

import click
from openai import OpenAI

from config import get_config, update_config
from service_integrations.base import BaseServiceIntegration


class OpenAIServiceIntegration(BaseServiceIntegration):
    """OpenAI service integration for AI summarization features.

    This integration provides AI-powered summarization capabilities
    but does NOT fetch work items or activities.
    """

    def get_name(self) -> str:
        """Get the name of the service integration."""
        return "OpenAI"

    def is_configured(self) -> bool:
        """Check if OpenAI API key is configured."""
        config = get_config()
        return bool(config.openai.openai_api_key)

    def setup(self) -> None:
        """Set up OpenAI configuration by asking for API key and preferences."""
        click.echo("\n=== OpenAI Configuration ===")
        click.echo(
            "OpenAI is used for AI-powered summarization of your work activities."
        )

        # Ask for API key
        api_key = click.prompt(
            "Enter your OpenAI API key",
            type=str,
            hide_input=True,
        )
        update_config("OPENAI_API_KEY", api_key)

        # Ask if custom base URL is needed (for Azure OpenAI, etc.)
        use_custom_url = click.confirm(
            "Do you want to use a custom OpenAI base URL? (e.g., for Azure OpenAI)",
            default=False,
        )

        if use_custom_url:
            base_url = click.prompt(
                "Enter your custom OpenAI base URL",
                type=str,
                default="https://api.openai.com/v1",
            )
            update_config("OPENAI_BASE_URL", base_url)
        else:
            update_config("OPENAI_BASE_URL", "https://api.openai.com/v1")

        # Optional: Ask for model preferences
        configure_models = click.confirm(
            "Do you want to configure custom models? (default: gpt-4o-mini for items, gpt-5 for overall summary)",
            default=False,
        )

        if configure_models:
            workitem_model = click.prompt(
                "Enter model for work item summaries",
                type=str,
                default="gpt-4o-mini",
            )
            update_config("OPENAI_WORKITEM_SUMMARY_MODEL", workitem_model)

            overall_model = click.prompt(
                "Enter model for overall summary",
                type=str,
                default="gpt-5",
            )
            update_config("OPENAI_SUMMARY_MODEL", overall_model)

        click.echo("✓ OpenAI configuration saved")

    def validate(self) -> bool:
        """Validate OpenAI configuration by testing the API connection.

        Returns:
            True if validation succeeds, False otherwise.
        """
        if not self.is_configured():
            click.echo("✗ OpenAI is not configured", err=True)
            return False

        try:
            config = get_config()
            client = OpenAI(
                base_url=config.openai.openai_base_url,
                api_key=config.openai.openai_api_key,
            )

            # Simple test call to verify authentication
            client.models.list()

            click.echo("✓ OpenAI connection validated successfully")
            return True

        except Exception as e:
            click.echo(f"✗ OpenAI validation failed: {str(e)}", err=True)
            return False
