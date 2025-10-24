"""OpenAI service integration for AI-powered summarization."""

import questionary
from openai import OpenAI

from config import get_config, update_config
from logger import get_logger
from service_integrations.base import BaseServiceIntegration

logger = get_logger(__name__)


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
        logger.info("\n=== OpenAI Configuration ===")
        logger.info(
            "OpenAI is used for AI-powered summarization of your work activities."
        )

        # Ask for API key
        api_key = questionary.password(
            "Enter your OpenAI API key:",
        ).ask()
        update_config("OPENAI_API_KEY", api_key)

        # Ask if custom base URL is needed (for Azure OpenAI, etc.)
        use_custom_url = questionary.confirm(
            "Do you want to use a custom OpenAI base URL? (e.g., for Azure OpenAI)",
            default=False,
        ).ask()

        if use_custom_url:
            base_url = questionary.text(
                "Enter your custom OpenAI base URL:",
                default="https://api.openai.com/v1",
            ).ask()
            update_config("OPENAI_BASE_URL", base_url)
        else:
            update_config("OPENAI_BASE_URL", "https://api.openai.com/v1")

        # Optional: Ask for model preferences
        configure_models = questionary.confirm(
            "Do you want to configure custom models? (default: gpt-4o-mini for items, gpt-5 for overall summary)",
            default=False,
        ).ask()

        if configure_models:
            workitem_model = questionary.text(
                "Enter model for work item summaries:",
                default="gpt-4o-mini",
            ).ask()
            update_config("OPENAI_WORKITEM_SUMMARY_MODEL", workitem_model)

            overall_model = questionary.text(
                "Enter model for overall summary:",
                default="gpt-5",
            ).ask()
            update_config("OPENAI_SUMMARY_MODEL", overall_model)

        logger.info("✓ OpenAI configuration saved")

    def validate(self) -> bool:
        """Validate OpenAI configuration by testing the API connection.

        Returns:
            True if validation succeeds, False otherwise.
        """
        if not self.is_configured():
            logger.error("✗ OpenAI is not configured")
            return False

        try:
            config = get_config()
            client = OpenAI(
                base_url=config.openai.openai_base_url,
                api_key=config.openai.openai_api_key,
            )

            # Simple test call to verify authentication
            client.models.list()

            logger.info("✓ OpenAI connection validated successfully")
            return True

        except Exception as e:
            logger.error(f"✗ OpenAI validation failed: {str(e)}")
            return False

    def disconnect(self) -> None:
        """Remove OpenAI configuration and reset to default settings."""
        update_config("OPENAI_API_KEY", "")
        update_config("OPENAI_BASE_URL", "https://api.openai.com/v1")
        update_config("OPENAI_WORKITEM_SUMMARY_MODEL", "gpt-4o-mini")
        update_config("OPENAI_SUMMARY_MODEL", "gpt-5")
