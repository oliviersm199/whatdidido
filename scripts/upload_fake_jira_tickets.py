#!/usr/bin/env python3
"""
Script to upload fake Jira tickets from CSV file for testing purposes.

This script reads the fake_jira_tickets.csv file and creates corresponding
tickets in Jira using the Jira Python SDK. It includes all metadata like
comments, story points, time tracking, labels, components, and sprints.

Usage:
    python scripts/upload_fake_jira_tickets.py
"""
import csv
import sys
import time
from datetime import datetime
from pathlib import Path

import click
from jira import JIRA
from jira.exceptions import JIRAError

# Add src to path so we can import config
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import get_config  # noqa: E402


def parse_comments(comment_string: str) -> list[str]:
    """Parse pipe-separated comments from CSV."""
    if not comment_string or comment_string.strip() == "":
        return []
    return [c.strip() for c in comment_string.split("|") if c.strip()]


def parse_labels(label_string: str) -> list[str]:
    """Parse semicolon-separated labels from CSV."""
    if not label_string or label_string.strip() == "":
        return []
    return [label.strip() for label in label_string.split(";") if label.strip()]


def parse_components(component_string: str) -> list[str]:
    """Parse semicolon-separated components from CSV."""
    if not component_string or component_string.strip() == "":
        return []
    return [c.strip() for c in component_string.split(";") if c.strip()]


def format_date_for_jira(date_string: str) -> str:
    """Convert ISO 8601 date to Jira format (YYYY-MM-DD)."""
    if not date_string or date_string.strip() == "":
        return ""
    # Parse ISO format and return just the date portion
    dt = datetime.fromisoformat(date_string.replace("Z", "+00:00"))
    return dt.strftime("%Y-%m-%d")


def create_jira_issue(
    jira_client: JIRA, row: dict, project_key: str, dry_run: bool = False
) -> str | None:
    """
    Create a single Jira issue from a CSV row.

    Args:
        jira_client: Authenticated JIRA client
        row: Dictionary containing issue data from CSV
        project_key: The Jira project key
        dry_run: If True, only print what would be created without actually creating

    Returns:
        The created issue key (e.g., 'KAN-123') or None if dry_run
    """
    issue_type = row["issue_type"]
    summary = row["summary"]
    description = row["description"]
    priority = row["priority"]
    status = row["status"]

    if dry_run:
        click.echo(f"\n[DRY RUN] Would create {issue_type}: {summary}")
        click.echo(f"  Status: {status}")
        click.echo(f"  Priority: {priority}")
        if row["labels"]:
            click.echo(f"  Labels: {row['labels']}")
        if row["story_points"]:
            click.echo(f"  Story Points: {row['story_points']}")
        if row["comments"]:
            comments = parse_comments(row["comments"])
            click.echo(f"  Comments: {len(comments)}")
        return None

    # Prepare issue fields
    issue_fields = {
        "project": {"key": project_key},
        "summary": summary,
        "description": description,
        "issuetype": {"name": issue_type},
    }

    # Add priority if specified
    if priority:
        issue_fields["priority"] = {"name": priority}

    # Add labels if specified
    labels = parse_labels(row["labels"])
    if labels:
        issue_fields["labels"] = labels

    try:
        # Create the issue
        click.echo(f"\nCreating {issue_type}: {summary}...", nl=False)
        new_issue = jira_client.create_issue(fields=issue_fields)
        click.echo(f" Created {new_issue.key}")

        # Add story points if specified (this is a custom field)
        # Note: Story points field ID varies by Jira instance
        # Common field IDs: customfield_10016, customfield_10026, etc.
        if row["story_points"]:
            try:
                story_points = float(row["story_points"])
                # Try common story points field IDs
                for field_id in ["customfield_10016", "customfield_10026"]:
                    try:
                        new_issue.update(fields={field_id: story_points})
                        click.echo(f"  Added story points: {story_points}")
                        break
                    except JIRAError:
                        continue
            except (ValueError, JIRAError) as e:
                click.echo(f"  Warning: Could not set story points: {e}", err=True)

        # Add time tracking if specified
        if row["time_spent_hours"]:
            try:
                hours = int(row["time_spent_hours"])
                if hours > 0:
                    # Log work in seconds (hours * 3600)
                    jira_client.add_worklog(
                        issue=new_issue.key,
                        timeSpentSeconds=hours * 3600,
                        comment="Time logged from test data",
                    )
                    click.echo(f"  Logged {hours} hours of work")
            except (ValueError, JIRAError) as e:
                click.echo(f"  Warning: Could not log work time: {e}", err=True)

        # Add comments if specified
        comments = parse_comments(row["comments"])
        for i, comment_text in enumerate(comments, 1):
            try:
                jira_client.add_comment(new_issue.key, comment_text)
                click.echo(f"  Added comment {i}/{len(comments)}")
            except JIRAError as e:
                click.echo(f"  Warning: Could not add comment {i}: {e}", err=True)

        # Transition to the desired status if not "To Do"
        if status and status != "To Do":
            try:
                transitions = jira_client.transitions(new_issue)
                # Find the transition that matches the desired status
                transition_id = None
                for trans in transitions:
                    if (
                        trans["name"].lower() == status.lower()
                        or trans["to"]["name"].lower() == status.lower()
                    ):
                        transition_id = trans["id"]
                        break

                if transition_id:
                    jira_client.transition_issue(new_issue.key, transition_id)
                    click.echo(f"  Transitioned to: {status}")
                else:
                    click.echo(
                        f"  Warning: Could not find transition to '{status}'",
                        err=True,
                    )
            except JIRAError as e:
                click.echo(f"  Warning: Could not transition issue: {e}", err=True)

        # Update resolved date if specified
        if row["resolved_date"]:
            try:
                resolved_date = format_date_for_jira(row["resolved_date"])
                if resolved_date:
                    # Note: Resolution date is typically set automatically by Jira
                    # This is just for reference
                    click.echo(f"  Resolved date: {resolved_date}")
            except Exception as e:
                click.echo(f"  Warning: Could not set resolved date: {e}", err=True)

        return new_issue.key

    except JIRAError as e:
        click.echo(" FAILED", err=True)
        click.echo(f"  Error: {e}", err=True)
        return None


@click.command()
@click.option(
    "--csv-file",
    type=click.Path(exists=True, path_type=Path),
    default=Path(__file__).parent.parent / "test_data" / "fake_jira_tickets.csv",
    help="Path to the CSV file containing fake ticket data",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be created without actually creating tickets",
)
@click.option(
    "--limit",
    type=int,
    default=None,
    help="Maximum number of tickets to create (useful for testing)",
)
def main(csv_file: Path, dry_run: bool, limit: int | None):
    """Upload fake Jira tickets from CSV file for testing purposes."""
    click.echo("=" * 60)
    click.echo("Fake Jira Ticket Upload Script")
    click.echo("=" * 60)

    # Load configuration
    try:
        config = get_config()
        if not config.jira.jira_url or not config.jira.jira_api_key:
            click.echo(
                "\nError: Jira configuration not found. Please run 'whatdidido connect' first.",
                err=True,
            )
            sys.exit(1)
    except Exception as e:
        click.echo(f"\nError loading configuration: {e}", err=True)
        sys.exit(1)

    # Connect to Jira
    if not dry_run:
        try:
            click.echo(f"\nConnecting to Jira at {config.jira.jira_url}...")
            jira_client = JIRA(
                server=config.jira.jira_url,
                basic_auth=(config.jira.jira_username, config.jira.jira_api_key),
            )
            click.echo("Successfully connected to Jira")
        except JIRAError as e:
            click.echo(f"\nError connecting to Jira: {e}", err=True)
            sys.exit(1)
    else:
        click.echo("\n[DRY RUN MODE] - No actual changes will be made")
        jira_client = None

    # Read CSV file
    click.echo(f"\nReading tickets from: {csv_file}")
    try:
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except Exception as e:
        click.echo(f"\nError reading CSV file: {e}", err=True)
        sys.exit(1)

    if not rows:
        click.echo("\nNo tickets found in CSV file", err=True)
        sys.exit(1)

    # Get project key from first row
    project_key = rows[0]["project_key"]
    click.echo(f"Target project: {project_key}")

    # Apply limit if specified
    if limit:
        rows = rows[:limit]
        click.echo(f"Limited to first {limit} tickets")

    click.echo(f"\nTotal tickets to create: {len(rows)}")

    # Confirm before proceeding
    if not dry_run:
        if not click.confirm(
            "\nThis will create tickets in your Jira instance. Continue?"
        ):
            click.echo("Aborted.")
            sys.exit(0)

    # Create issues
    created_count = 0
    failed_count = 0

    for i, row in enumerate(rows, 1):
        click.echo(f"\n[{i}/{len(rows)}]", nl="")
        result = create_jira_issue(jira_client, row, project_key, dry_run)
        if result:
            created_count += 1
        elif not dry_run:
            failed_count += 1
        time.sleep(0.5)  # To avoid hitting rate limits

    # Summary
    click.echo("\n" + "=" * 60)
    click.echo("Summary")
    click.echo("=" * 60)
    if dry_run:
        click.echo(f"Would have created: {len(rows)} tickets")
    else:
        click.echo(f"Successfully created: {created_count} tickets")
        if failed_count > 0:
            click.echo(f"Failed: {failed_count} tickets")
        click.echo(
            f"\nView your tickets at: {config.jira.jira_url}/projects/{project_key}"
        )


if __name__ == "__main__":
    main()
