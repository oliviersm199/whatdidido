from datetime import date, datetime, timedelta

import click
import questionary

from config import get_config
from models.fetch_params import FetchParams
from providers import get_provider
from providers.jira import JiraProvider
from providers.linear import LinearProvider
from service_integrations.openai import OpenAIServiceIntegration
from services.clean_service import CleanService
from services.config_service import ConfigService
from services.connect_service import ConnectService
from services.disconnect_service import DisconnectService
from services.report_service import ReportService
from services.sync_service import SyncService

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
    connect_service = ConnectService()

    # Step 1: Setup data source integrations
    provider_question = questionary.checkbox(
        "Which data sources would you like to connect?",
        choices=[integration().get_name() for integration in registered_integrations],
    )
    selected_integration_names = provider_question.ask()

    # Get provider instances for selected integrations
    selected_providers = [get_provider(name) for name in selected_integration_names]

    if selected_providers:
        click.echo("Starting setup for selected data sources...")
        configured, errors = connect_service.setup_providers(selected_providers)

        for provider_name in configured:
            click.echo(f"✓ {provider_name} configured successfully")

        for provider_name, error in errors.items():
            click.echo(f"Error setting up {provider_name}: {error}", err=True)

    # Step 2: Setup service integrations (AI, notifications, etc.)
    service_question = questionary.checkbox(
        "\nWhich service integrations would you like to configure?",
        choices=[service().get_name() for service in registered_service_integrations],
    )
    selected_service_names = service_question.ask()

    # Get service instances for selected services
    selected_services = []
    for service_name in selected_service_names:
        for service_cls in registered_service_integrations:
            if service_cls().get_name() == service_name:
                selected_services.append(service_cls())
                break

    if selected_services:
        click.echo("\nStarting setup for selected service integrations...")

        # Ask if they want to validate
        validate = questionary.confirm(
            "Would you like to validate service configurations after setup?",
            default=True,
        ).ask()

        configured, errors = connect_service.setup_services(
            selected_services, validate=validate
        )

        for service_name in configured:
            click.echo(f"✓ {service_name} configured successfully")

        for service_name, error in errors.items():
            click.echo(f"Error setting up {service_name}: {error}", err=True)

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
    # Use SyncService to get authenticated providers
    sync_service = SyncService()
    authenticated_providers = sync_service.get_authenticated_providers(
        registered_integrations
    )

    if not authenticated_providers:
        click.echo(
            "No authenticated integrations found. Please run 'init' command first.",
            err=True,
        )
        return

    joined_integrations = ", ".join([p.get_name() for p in authenticated_providers])

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

    # Use SyncService to sync all providers
    results = sync_service.sync_all_providers(authenticated_providers, fetch_params)

    # Display results
    for result in results:
        if result.success:
            click.echo(
                f"Data sync from {result.provider_name} complete! Saved {result.count} work items."
            )
        else:
            click.echo(
                f"Error syncing data from {result.provider_name}: {result.error}",
                err=True,
            )

    click.echo("All data sources have been synchronized.")


@main.command("config")
def show_config():
    """
    Display current configuration (with sensitive keys anonymized)
    """
    from config import CONFIG_FILE

    config_service = ConfigService(CONFIG_FILE)

    if not config_service.file_exists():
        click.echo(
            "No configuration file found. Please run 'init' command first.", err=True
        )
        return

    click.echo(f"Configuration file: {CONFIG_FILE}\n")

    if config_service.is_empty():
        click.echo("Configuration file is empty.")
        return

    lines = config_service.get_config_lines()
    for line in lines:
        click.echo(line)


@main.command("clean")
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
def clean(confirm: bool):
    """
    Clean up whatdidido data files (JSON data and markdown reports)
    """
    clean_service = CleanService()

    files_to_delete = clean_service.get_files_to_clean()

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

    # Delete files using CleanService
    result = clean_service.clean()

    if result.success:
        for file in result.deleted_files:
            click.echo(f"Deleted: {file}")
        click.echo("\nCleanup complete!")
    else:
        for file, error in result.errors.items():
            click.echo(f"Error deleting {file}: {error}", err=True)


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
        return

    # Use ReportService to generate the report
    report_service = ReportService()

    click.echo("Generating summaries for each work item...\n")

    result = report_service.generate_report()

    if not result.success:
        click.echo(f"Error generating report: {result.error}", err=True)
        return

    click.echo(
        f"Found {result.work_item_count} work items across {result.provider_count} provider(s)."
    )
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

    disconnect_service = DisconnectService()

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

    # Get configured providers and services
    provider_classes = registered_integrations if data_sources else []
    service_classes = registered_service_integrations if services else []

    configured_providers = disconnect_service.get_configured_providers(provider_classes)
    configured_services = disconnect_service.get_configured_services(service_classes)

    if not configured_providers and not configured_services:
        click.echo("No configured integrations found to disconnect.")
        return

    # Show what will be disconnected
    click.echo("The following integrations will be disconnected:")
    for provider in configured_providers:
        click.echo(f"  - {provider.get_name()} data source")
    for service in configured_services:
        click.echo(f"  - {service.get_name()} service")

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
    result = disconnect_service.disconnect_all(
        provider_classes=provider_classes,
        service_classes=service_classes,
    )

    # Display results
    for provider_name in result.disconnected_providers:
        click.echo(f"Disconnected: {provider_name}")

    for service_name in result.disconnected_services:
        click.echo(f"Disconnected: {service_name}")

    # Display errors
    for name, error in result.errors.items():
        click.echo(f"Error disconnecting {name}: {error}", err=True)

    click.echo(
        f"\nDisconnect complete! Removed {result.total_disconnected} integration(s)."
    )
    click.echo("Run 'init' to reconnect any integrations.")


if __name__ == "__main__":
    main()
