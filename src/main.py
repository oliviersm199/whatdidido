import click
import questionary

from providers import get_provider
from providers.jira import JiraProvider

registered_integrations = [JiraProvider]


@click.group()
def main():
    """What did I do again? - Track your work across JIRA and GitHub"""
    pass


@main.command("init")
def init():
    """
    Guided step by step instructions on how to setup repository
    """
    available_integrations = [integration for integration in registered_integrations]
    provider_question = questionary.checkbox(
        "Which provider would you like to connect?",
        choices=[integration().get_name() for integration in available_integrations],
    )
    selected_integrations = provider_question.ask()

    click.echo("Starting setup for selected integrations...")

    for integration in selected_integrations:
        click.echo(f"Setting up {integration}...")
        provider = get_provider(integration)
        provider.setup()
        click.echo(f"{integration} setup complete!")

    click.echo("All selected integrations have been set up.")


@main.command("sync")
def sync():
    """
    Sync issues and pull requests between JIRA and GitHub
    """


@main.command("report")
def report():
    """
    Generate a report of your activities from JIRA and GitHub
    """


if __name__ == "__main__":
    main()
