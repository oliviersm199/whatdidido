import click
import questionary
from persist import DataStore

from config import get_config
from providers import get_provider
from providers.jira import JiraProvider
from summarize import OverallSummarizer, WorkItemSummarizer

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
@click.option(
    "--start-date",
    default=None,
    help="Start date for syncing (format: YYYY-MM-DD)",
)
@click.option(
    "--end-date",
    default=None,
    help="End date for syncing (format: YYYY-MM-DD)",
)
def sync(start_date: str | None, end_date: str | None):
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

    data_store = DataStore()

    for integration in authenticated_integrations:
        integration_instance = integration()
        provider_name = integration_instance.get_name()

        click.echo(f"Syncing data from {provider_name}...")
        try:
            count = data_store.save_provider_data(
                integration_instance, start_date, end_date
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


@main.command("report")
def report():
    """
    Generate a report of your activities from JIRA and GitHub
    """
    # Validate OpenRouter API key is configured
    config = get_config()
    if not config.openrouter.openrouter_api_key:
        click.echo(
            "OpenRouter API key is not set.",
            err=True,
        )
        # Prompt for API key
        api_key = questionary.password("Enter your OpenRouter API key:").ask()
        if not api_key:
            click.echo("API key is required to generate reports.", err=True)
            return

        # Save to config
        from config import update_config

        update_config("OPENROUTER_API_KEY", api_key)
        click.echo("OpenRouter API key has been saved to config.")

        # Reload config to get the updated value
        config = get_config()

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

    # Step 1: Generate individual work item summaries
    summarizer = WorkItemSummarizer()
    work_item_summaries = summarizer.summarize_work_items(all_work_items)

    # Step 2: Generate overall summary from individual summaries
    click.echo("\nGenerating overall summary...")
    overall_summarizer = OverallSummarizer()
    overall_summarizer.generate_and_save_summary(work_item_summaries)

    click.echo("\nReport generation complete. Summary saved to whatdidido.md")


if __name__ == "__main__":
    main()
