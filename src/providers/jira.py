import click
import jira
import questionary

from config import get_config, update_config
from providers.base import BaseProvider


class JiraProvider(BaseProvider):
    async def fetch_items(self, start_date, end_date):
        # Implementation for fetching Jira issues
        pass

    def authenticate(self) -> bool:
        config = get_config()
        try:
            self.jira_client = jira.JIRA(
                server=config.jira.jira_url,
                basic_auth=(config.jira.jira_username, config.jira.jira_api_key),
            )
            server_info = self.jira_client.server_info()
            click.echo(f"Connected to Jira server version: {server_info['version']}")
            return True
        except jira.JIRAError as e:
            click.echo(f"Failed to authenticate with Jira: {e}", err=True)
            return False

    def is_configured(self) -> bool:
        config = get_config()
        return (
            config.jira.jira_url != ""
            and config.jira.jira_username != ""
            and config.jira.jira_api_key != ""
        )

    def setup(self):
        """
        Let's review the config and see what values are set in the config file.
        """
        is_configured = self.is_configured()
        confirm_configured = False
        if is_configured:
            confirm_configured = click.confirm(
                "Jira is already configured. Do you want to reconfigure it?",
                default=False,
            )
        if not is_configured or confirm_configured:
            credentials = ask_jira_credentials()
            update_config("JIRA_URL", credentials["server"])
            update_config("JIRA_USERNAME", credentials["username"])
            update_config("JIRA_API_KEY", credentials["api_token"])

        if self.authenticate():
            click.echo("Jira has been successfully configured.")

    def get_name(self) -> str:
        return "Jira"


def ask_jira_credentials():
    jira_url = questionary.text(
        "Enter your Jira URL (e.g., https://your-domain.atlassian.net):"
    ).ask()
    jira_username = questionary.text("Enter your Jira username (email):").ask()
    jira_api_key = questionary.password("Enter your Jira API token:").ask()

    return {
        "server": jira_url,
        "username": jira_username,
        "api_token": jira_api_key,
    }
