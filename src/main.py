from datetime import date, datetime, timedelta

import click
import questionary

from config import get_config, update_config
from persist import DataStore
from providers import get_provider
from providers.jira import JiraProvider
from providers.linear import LinearProvider
from summarize import OverallSummarizer, WorkItemSummarizer

registered_integrations = [JiraProvider, LinearProvider]


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

    # Setup OpenAI configuration
    click.echo("\nSetting up OpenAI-compatible API configuration...")
    click.echo(
        "This is used for generating summaries. Compatible with OpenAI, OpenRouter, or any OpenAI-compatible API."
    )

    api_key = questionary.password("Enter your API key:").ask()
    if not api_key:
        click.echo("API key is required for report generation.", err=True)
        return

    # Ask if user wants to set a custom base URL
    use_custom_base = questionary.confirm(
        "Do you want to use a custom base URL? (e.g., https://openrouter.ai/api/v1)",
        default=False,
    ).ask()

    base_url = None
    if use_custom_base:
        base_url = questionary.text(
            "Enter your base URL:", default="https://api.openai.com/v1"
        ).ask()

    # Save OpenAI configuration
    update_config("OPENAI_API_KEY", api_key)
    if base_url:
        update_config("OPENAI_BASE_URL", base_url)

    click.echo("API configuration saved!")


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
def sync(start_date: datetime | None, end_date: datetime | None):
    """
    Sync issues and pull requests between JIRA and GitHub
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
    click.echo(f"Starting synchronization for data sources: {joined_integrations}...")

    # Convert datetime to date, defaulting to one year back if not provided
    parsed_start_date = (
        start_date.date() if start_date else (date.today() - timedelta(days=365))
    )
    parsed_end_date = end_date.date() if end_date else date.today()

    data_store = DataStore()

    for integration in authenticated_integrations:
        integration_instance = integration()
        provider_name = integration_instance.get_name()

        click.echo(f"Syncing data from {provider_name}...")
        try:
            count = data_store.save_provider_data(
                integration_instance, parsed_start_date, parsed_end_date
            )
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
        click.echo("No configuration file found. Please run 'init' command first.", err=True)
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
@click.option(
    "--confirm",
    is_flag=True,
    help="Skip confirmation prompt"
)
def clean(confirm: bool):
    """
    Clean up whatdidido data files (JSON data and markdown reports)
    """
    from pathlib import Path

    # Files to clean up
    json_file = Path("whatdidido.json")
    json_lock = Path("whatdidido.json.lock")
    md_file = Path("whatdidido.md")

    files_to_delete = []
    if json_file.exists():
        files_to_delete.append(json_file)
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
            "\nAre you sure you want to delete these files?",
            default=False
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


if __name__ == "__main__":
    main()
