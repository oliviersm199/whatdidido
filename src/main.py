from datetime import date, datetime, timedelta

import click
import questionary

from config import get_config
from models.fetch_params import FetchParams
from persist import DataStore
from providers import get_provider
from providers.jira import JiraProvider
from providers.linear import LinearProvider
from service_integrations.openai import OpenAIServiceIntegration
from summarize import OverallSummarizer, WorkItemSummarizer

# Data source integrations (for syncing work items)
registered_integrations = [JiraProvider, LinearProvider]

# Service integrations (for AI, notifications, etc.)
registered_service_integrations = [OpenAIServiceIntegration]


@click.group()
def main():
    """What did I do again? - Track your work across JIRA and GitHub"""
    pass


@main.command("connect")
def connect():
    """
    Guided step by step instructions on how to setup repository
    """
    # Step 1: Setup data source integrations
    available_integrations = [integration for integration in registered_integrations]
    provider_question = questionary.checkbox(
        "Which data sources would you like to connect?",
        choices=[integration().get_name() for integration in available_integrations],
    )
    selected_integrations = provider_question.ask()

    click.echo("Starting setup for selected data sources...")

    for integration in selected_integrations:
        click.echo(f"Setting up {integration}...")
        provider = get_provider(integration)
        provider.setup()

    # Step 2: Setup service integrations (AI, notifications, etc.)
    available_services = [service for service in registered_service_integrations]
    service_question = questionary.checkbox(
        "\nWhich service integrations would you like to configure?",
        choices=[service().get_name() for service in available_services],
    )
    selected_services = service_question.ask()

    if selected_services:
        click.echo("\nStarting setup for selected service integrations...")

        for service_name in selected_services:
            click.echo(f"\nSetting up {service_name}...")
            # Find the service class
            service_instance = None
            for service_cls in available_services:
                if service_cls().get_name() == service_name:
                    service_instance = service_cls()
                    break

            if service_instance:
                service_instance.setup()
                # Optionally validate the configuration
                if questionary.confirm(
                    f"Would you like to validate {service_name} configuration?",
                    default=True,
                ).ask():
                    service_instance.validate()
            else:
                click.echo(f"Error: Could not find service {service_name}", err=True)

    click.echo("\n✓ Setup complete!")


@main.command("sync")
@click.option(
    "--start-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=None,
    help="Start date for syncing (format: YYYY-MM-DD)",
)
@click.option(
    "--end-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=None,
    help="End date for syncing (format: YYYY-MM-DD)",
)
@click.option(
    "--user",
    type=str,
    default=None,
    help="User email to sync for (default: authenticated user). Works across Jira and Linear.",
)
def sync(start_date: datetime | None, end_date: datetime | None, user: str | None):
    """
    Sync issues and pull requests from Jira and Linear
    """
    available_integrations = [integration for integration in registered_integrations]
    authenticated_integrations = [
        integration
        for integration in available_integrations
        if integration().is_configured() and integration().authenticate()
    ]
    if not authenticated_integrations:
        click.echo(
            "No authenticated integrations found. Please run 'init' command first.",
            err=True,
        )
        return
    joined_integrations = ", ".join(
        [integration().get_name() for integration in authenticated_integrations]
    )

    # Show who we're syncing for
    user_msg = f" for user: {user}" if user else " (authenticated user)"
    click.echo(
        f"Starting synchronization for data sources: {joined_integrations}{user_msg}"
    )

    # Convert datetime to date, defaulting to one year back if not provided
    parsed_start_date = (
        start_date.date() if start_date else (date.today() - timedelta(days=365))
    )
    parsed_end_date = end_date.date() if end_date else date.today()

    # Create fetch parameters
    fetch_params = FetchParams(
        start_date=parsed_start_date,
        end_date=parsed_end_date,
        user_filter=user,
    )

    data_store = DataStore()

    for integration in authenticated_integrations:
        integration_instance = integration()
        provider_name = integration_instance.get_name()

        click.echo(f"Syncing data from {provider_name}...")
        try:
            count = data_store.save_provider_data(integration_instance, fetch_params)
            click.echo(
                f"Data sync from {provider_name} complete! Saved {count} work items."
            )
        except Exception as e:
            click.echo(
                f"Error syncing data from {provider_name}: {e}",
                err=True,
            )

    click.echo("All data sources have been synchronized.")


@main.command("config")
def show_config():
    """
    Display current configuration (with sensitive keys anonymized)
    """
    from config import CONFIG_FILE

    if not CONFIG_FILE.exists():
        click.echo(
            "No configuration file found. Please run 'init' command first.", err=True
        )
        return

    click.echo(f"Configuration file: {CONFIG_FILE}\n")

    with open(CONFIG_FILE, "r") as f:
        lines = f.readlines()

    if not lines:
        click.echo("Configuration file is empty.")
        return

    # Keys that should be anonymized
    sensitive_keys = ["API_KEY", "TOKEN", "PASSWORD"]

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            click.echo(line)
            continue

        if "=" in line:
            key, value = line.split("=", 1)
            # Check if this is a sensitive key
            if any(sensitive in key.upper() for sensitive in sensitive_keys):
                if value:
                    # Show first 4 and last 4 characters
                    if len(value) > 8:
                        anonymized = f"{value[:4]}...{value[-4:]}"
                    else:
                        anonymized = "****"
                    click.echo(f"{key}={anonymized}")
                else:
                    click.echo(f"{key}=")
            else:
                click.echo(line)
        else:
            click.echo(line)


@main.command("clean")
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
def clean(confirm: bool):
    """
    Clean up whatdidido data files (JSON data and markdown reports)
    """
    from pathlib import Path

    # Files to clean up
    json_file = Path("whatdidido.json")
    summary_file = Path("whatdidido-summary.json")
    json_lock = Path("whatdidido.json.lock")
    md_file = Path("whatdidido.md")

    files_to_delete = []
    if json_file.exists():
        files_to_delete.append(json_file)
    if summary_file.exists():
        files_to_delete.append(summary_file)
    if json_lock.exists():
        files_to_delete.append(json_lock)
    if md_file.exists():
        files_to_delete.append(md_file)

    if not files_to_delete:
        click.echo("No whatdidido files found to clean up.")
        return

    click.echo("The following files will be deleted:")
    for file in files_to_delete:
        click.echo(f"  - {file}")

    if not confirm:
        confirmed = questionary.confirm(
            "\nAre you sure you want to delete these files?", default=False
        ).ask()
        if not confirmed:
            click.echo("Cleanup cancelled.")
            return

    # Delete files
    for file in files_to_delete:
        try:
            file.unlink()
            click.echo(f"Deleted: {file}")
        except Exception as e:
            click.echo(f"Error deleting {file}: {e}", err=True)

    click.echo("\nCleanup complete!")


@main.command("report")
def report():
    """
    Generate a report of your activities from JIRA and GitHub
    """
    # Validate OpenAI API key is configured
    config = get_config()
    if not config.openai.openai_api_key:
        click.echo(
            "OpenAI API key is not set, please run the init.",
            err=True,
        )

    data_store = DataStore()
    work_items_by_provider = data_store.get_all_data()

    if not work_items_by_provider:
        click.echo("No work items found. Please run 'sync' command first.", err=True)
        return

    # Flatten all work items from all providers into a single list
    all_work_items = []
    for _, items in work_items_by_provider.items():
        all_work_items.extend(items)

    click.echo(
        f"Found {len(all_work_items)} work items across {len(work_items_by_provider)} provider(s)."
    )
    click.echo("Generating summaries for each work item...\n")

    summarizer = WorkItemSummarizer()
    work_item_summaries = summarizer.summarize_work_items(all_work_items)

    click.echo("\nGenerating overall summary...")
    overall_summarizer = OverallSummarizer()
    overall_summarizer.generate_and_save_summary(work_item_summaries)

    click.echo("\nReport generation complete. Summary saved to whatdidido.md")


@main.command("disconnect")
@click.option(
    "--data-sources",
    is_flag=True,
    help="Disconnect data source integrations (Jira, Linear, etc.)",
)
@click.option(
    "--services",
    is_flag=True,
    help="Disconnect service integrations (OpenAI, etc.)",
)
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
def disconnect(data_sources: bool, services: bool, confirm: bool):
    """
    Disconnect (wipe) data source and/or service integrations
    """
    from config import CONFIG_FILE

    # If neither flag is set, ask the user what they want to disconnect
    if not data_sources and not services:
        disconnect_choices = questionary.checkbox(
            "What would you like to disconnect?",
            choices=[
                "Data sources (Jira, Linear, etc.)",
                "Service integrations (OpenAI, etc.)",
            ],
        ).ask()

        if not disconnect_choices:
            click.echo("No integrations selected. Disconnect cancelled.")
            return

        data_sources = "Data sources (Jira, Linear, etc.)" in disconnect_choices
        services = "Service integrations (OpenAI, etc.)" in disconnect_choices

    # Check if config file exists
    if not CONFIG_FILE.exists():
        click.echo("No configuration file found. Nothing to disconnect.")
        return

    # Build list of what will be removed
    items_to_remove = []

    if data_sources:
        for integration in registered_integrations:
            integration_instance = integration()
            if integration_instance.is_configured():
                items_to_remove.append(
                    f"  - {integration_instance.get_name()} data source"
                )

    if services:
        for service in registered_service_integrations:
            service_instance = service()
            if service_instance.is_configured():
                items_to_remove.append(f"  - {service_instance.get_name()} service")

    if not items_to_remove:
        click.echo("No configured integrations found to disconnect.")
        return

    # Show what will be disconnected
    click.echo("The following integrations will be disconnected:")
    for item in items_to_remove:
        click.echo(item)

    # Confirm with user
    if not confirm:
        confirmed = questionary.confirm(
            "\nAre you sure you want to disconnect these integrations? This will remove all stored credentials.",
            default=False,
        ).ask()
        if not confirmed:
            click.echo("Disconnect cancelled.")
            return

    # Perform the disconnect
    disconnected_count = 0

    if data_sources:
        for integration in registered_integrations:
            integration_instance = integration()
            if integration_instance.is_configured():
                provider_name = integration_instance.get_name()

                try:
                    integration_instance.disconnect()
                    click.echo(f"Disconnected: {provider_name}")
                    disconnected_count += 1
                except Exception as e:
                    click.echo(f"Error disconnecting {provider_name}: {e}", err=True)

    if services:
        for service in registered_service_integrations:
            service_instance = service()
            if service_instance.is_configured():
                service_name = service_instance.get_name()

                try:
                    service_instance.disconnect()
                    click.echo(f"Disconnected: {service_name}")
                    disconnected_count += 1
                except Exception as e:
                    click.echo(f"Error disconnecting {service_name}: {e}", err=True)

    click.echo(f"\nDisconnect complete! Removed {disconnected_count} integration(s).")
    click.echo("Run 'init' to reconnect any integrations.")


if __name__ == "__main__":
    main()
