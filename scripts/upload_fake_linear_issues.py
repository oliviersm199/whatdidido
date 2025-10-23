#!/usr/bin/env python3
"""
Script to upload fake Linear issues from CSV file for testing purposes.

This script reads the fake_linear_issues.csv file and creates corresponding
issues in Linear using the GraphQL API. It includes all metadata like
comments, estimates, labels, projects, and cycles.

Usage:
    python scripts/upload_fake_linear_issues.py
"""
import csv
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import click
import requests

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


def make_graphql_request(
    api_key: str, query: str, variables: dict | None = None
) -> dict:
    """Make a GraphQL request to Linear API."""
    url = "https://api.linear.app/graphql"
    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json",
    }

    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    click.echo(f"  [DEBUG] Making GraphQL request with variables: {json.dumps(variables, indent=2) if variables else 'None'}", err=True)

    response = requests.post(url, json=payload, headers=headers)

    click.echo(f"  [DEBUG] Response status: {response.status_code}", err=True)

    response.raise_for_status()

    result = response.json()

    click.echo(f"  [DEBUG] Response data: {json.dumps(result, indent=2)}", err=True)

    if "errors" in result:
        raise Exception(f"GraphQL errors: {json.dumps(result['errors'], indent=2)}")

    return result


def get_or_create_team(api_key: str, team_key: str) -> str:
    """Get team ID by key, or return None if not found."""
    click.echo(f"  [DEBUG] Looking up team with key: {team_key}", err=True)
    query = """
    query($teamKey: String!) {
        teams(filter: { key: { eq: $teamKey } }) {
            nodes {
                id
                key
                name
            }
        }
    }
    """
    result = make_graphql_request(api_key, query, {"teamKey": team_key})
    teams = result.get("data", {}).get("teams", {}).get("nodes", [])

    if teams:
        click.echo(f"  [DEBUG] Found team: {teams[0]['name']} (ID: {teams[0]['id']})", err=True)
        return teams[0]["id"]

    raise Exception(
        f"Team '{team_key}' not found. Please create the team in Linear first."
    )


def get_or_create_project(api_key: str, team_id: str, project_name: str) -> str | None:
    """Get or create a project by name."""
    if not project_name or project_name.strip() == "":
        click.echo(f"  [DEBUG] No project name specified, skipping project creation", err=True)
        return None

    click.echo(f"  [DEBUG] Looking for project: {project_name}", err=True)

    # First, try to find existing project
    query = """
    query($teamId: ID!) {
        projects(filter: { team: { id: { eq: $teamId } } }) {
            nodes {
                id
                name
            }
        }
    }
    """
    result = make_graphql_request(api_key, query, {"teamId": team_id})
    projects = result.get("data", {}).get("projects", {}).get("nodes", [])

    click.echo(f"  [DEBUG] Found {len(projects)} existing projects", err=True)

    for project in projects:
        if project["name"] == project_name:
            click.echo(f"  [DEBUG] Found existing project: {project_name} (ID: {project['id']})", err=True)
            return project["id"]

    # Create new project if not found
    click.echo(f"  [DEBUG] Project not found, creating new project: {project_name}", err=True)
    create_query = """
    mutation($teamId: ID!, $name: String!) {
        projectCreate(input: { teamIds: [$teamId], name: $name }) {
            success
            project {
                id
                name
            }
        }
    }
    """
    result = make_graphql_request(
        api_key, create_query, {"teamId": team_id, "name": project_name}
    )
    project_id = result.get("data", {}).get("projectCreate", {}).get("project", {}).get("id")
    click.echo(f"  [DEBUG] Created project with ID: {project_id}", err=True)
    return project_id


def get_or_create_cycle(
    api_key: str, team_id: str, cycle_name: str
) -> str | None:
    """Get or create a cycle by name."""
    if not cycle_name or cycle_name.strip() == "":
        return None

    # First, try to find existing cycle
    query = """
    query($teamId: ID!) {
        cycles(filter: { team: { id: { eq: $teamId } } }) {
            nodes {
                id
                name
                number
            }
        }
    }
    """
    result = make_graphql_request(api_key, query, {"teamId": team_id})
    cycles = result.get("data", {}).get("cycles", {}).get("nodes", [])

    for cycle in cycles:
        if cycle["name"] == cycle_name:
            return cycle["id"]

    # Note: Creating cycles requires start/end dates, so we'll just return None
    # and log a warning. Users should create cycles manually in Linear.
    click.echo(
        f"  Warning: Cycle '{cycle_name}' not found. Issue will be created without a cycle.",
        err=True,
    )
    return None


def get_or_create_labels(api_key: str, team_id: str, label_names: list[str]) -> list[str]:
    """Get or create labels by name, return list of label IDs."""
    if not label_names:
        click.echo(f"  [DEBUG] No labels specified", err=True)
        return []

    click.echo(f"  [DEBUG] Processing {len(label_names)} labels: {label_names}", err=True)

    # Get all existing labels for the team
    query = """
    query($teamId: ID!) {
        issueLabels(filter: { team: { id: { eq: $teamId } } }) {
            nodes {
                id
                name
            }
        }
    }
    """
    result = make_graphql_request(api_key, query, {"teamId": team_id})
    existing_labels = result.get("data", {}).get("issueLabels", {}).get("nodes", [])

    click.echo(f"  [DEBUG] Found {len(existing_labels)} existing labels in team", err=True)

    label_map = {label["name"]: label["id"] for label in existing_labels}
    label_ids = []

    for label_name in label_names:
        if label_name in label_map:
            click.echo(f"  [DEBUG] Found existing label: {label_name} (ID: {label_map[label_name]})", err=True)
            label_ids.append(label_map[label_name])
        else:
            # Create new label
            click.echo(f"  [DEBUG] Creating new label: {label_name}", err=True)
            create_query = """
            mutation($teamId: ID!, $name: String!) {
                issueLabelCreate(input: { teamId: $teamId, name: $name }) {
                    success
                    issueLabel {
                        id
                        name
                    }
                }
            }
            """
            result = make_graphql_request(
                api_key, create_query, {"teamId": team_id, "name": label_name}
            )
            new_label_id = (
                result.get("data", {})
                .get("issueLabelCreate", {})
                .get("issueLabel", {})
                .get("id")
            )
            if new_label_id:
                label_ids.append(new_label_id)
                click.echo(f"  Created new label: {label_name} (ID: {new_label_id})")
            else:
                click.echo(f"  [ERROR] Failed to create label: {label_name}", err=True)

    click.echo(f"  [DEBUG] Final label IDs: {label_ids}", err=True)
    return label_ids


def get_workflow_state_id(api_key: str, team_id: str, state_name: str) -> str:
    """Get workflow state ID by name."""
    query = """
    query($teamId: ID!) {
        workflowStates(filter: { team: { id: { eq: $teamId } } }) {
            nodes {
                id
                name
                type
            }
        }
    }
    """
    result = make_graphql_request(api_key, query, {"teamId": team_id})
    states = result.get("data", {}).get("workflowStates", {}).get("nodes", [])

    # Try exact match first
    for state in states:
        if state["name"].lower() == state_name.lower():
            return state["id"]

    # Try type match as fallback
    state_type_map = {
        "backlog": "backlog",
        "todo": "unstarted",
        "in progress": "started",
        "in review": "started",
        "done": "completed",
        "canceled": "canceled",
    }

    target_type = state_type_map.get(state_name.lower())
    if target_type:
        for state in states:
            if state["type"] == target_type:
                return state["id"]

    # Default to first state
    if states:
        click.echo(
            f"  Warning: State '{state_name}' not found, using '{states[0]['name']}'",
            err=True,
        )
        return states[0]["id"]

    raise Exception(f"No workflow states found for team {team_id}")


def create_linear_issue(
    api_key: str, row: dict, team_id: str, dry_run: bool = False
) -> str | None:
    """
    Create a single Linear issue from a CSV row.

    Args:
        api_key: Linear API key
        row: Dictionary containing issue data from CSV
        team_id: The Linear team ID
        dry_run: If True, only print what would be created without actually creating

    Returns:
        The created issue identifier (e.g., 'ENG-123') or None if dry_run
    """
    title = row["title"]
    description = row["description"]
    priority = int(row["priority"]) if row["priority"] else 0
    state = row["state"]

    if dry_run:
        click.echo(f"\n[DRY RUN] Would create issue: {title}")
        click.echo(f"  State: {state}")
        click.echo(f"  Priority: {priority}")
        if row["labels"]:
            click.echo(f"  Labels: {row['labels']}")
        if row["estimate"]:
            click.echo(f"  Estimate: {row['estimate']}")
        if row["comments"]:
            comments = parse_comments(row["comments"])
            click.echo(f"  Comments: {len(comments)}")
        return None

    try:
        # Get or create project
        project_id = None
        if row["project_name"]:
            project_id = get_or_create_project(api_key, team_id, row["project_name"])

        # Get or create cycle
        cycle_id = None
        if row["cycle_name"]:
            cycle_id = get_or_create_cycle(api_key, team_id, row["cycle_name"])

        # Get or create labels
        label_names = parse_labels(row["labels"])
        label_ids = get_or_create_labels(api_key, team_id, label_names)

        # Get workflow state ID
        state_id = get_workflow_state_id(api_key, team_id, state)

        # Create the issue
        click.echo(f"\nCreating issue: {title}...", nl=False)

        mutation = """
        mutation($teamId: ID!, $title: String!, $description: String, $priority: Int, $stateId: ID!, $estimate: Int, $projectId: ID, $cycleId: ID, $labelIds: [ID!]) {
            issueCreate(input: {
                teamId: $teamId
                title: $title
                description: $description
                priority: $priority
                stateId: $stateId
                estimate: $estimate
                projectId: $projectId
                cycleId: $cycleId
                labelIds: $labelIds
            }) {
                success
                issue {
                    id
                    identifier
                    title
                }
            }
        }
        """

        variables = {
            "teamId": team_id,
            "title": title,
            "description": description,
            "priority": priority,
            "stateId": state_id,
            "estimate": int(row["estimate"]) if row["estimate"] else None,
            "projectId": project_id,
            "cycleId": cycle_id,
            "labelIds": label_ids if label_ids else None,
        }

        result = make_graphql_request(api_key, mutation, variables)
        issue_data = result.get("data", {}).get("issueCreate", {}).get("issue", {})
        issue_id = issue_data.get("id")
        issue_identifier = issue_data.get("identifier")

        click.echo(f" Created {issue_identifier}")

        # Add comments if specified
        comments = parse_comments(row["comments"])
        for i, comment_text in enumerate(comments, 1):
            try:
                comment_mutation = """
                mutation($issueId: ID!, $body: String!) {
                    commentCreate(input: { issueId: $issueId, body: $body }) {
                        success
                        comment {
                            id
                        }
                    }
                }
                """
                make_graphql_request(
                    api_key,
                    comment_mutation,
                    {"issueId": issue_id, "body": comment_text},
                )
                click.echo(f"  Added comment {i}/{len(comments)}")
                time.sleep(0.2)  # Small delay between comments
            except Exception as e:
                click.echo(f"  Warning: Could not add comment {i}: {e}", err=True)

        return issue_identifier

    except Exception as e:
        click.echo(" FAILED", err=True)
        click.echo(f"  Error: {e}", err=True)
        return None


@click.command()
@click.option(
    "--csv-file",
    type=click.Path(exists=True, path_type=Path),
    default=Path(__file__).parent.parent / "test_data" / "fake_linear_issues.csv",
    help="Path to the CSV file containing fake issue data",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be created without actually creating issues",
)
@click.option(
    "--limit",
    type=int,
    default=None,
    help="Maximum number of issues to create (useful for testing)",
)
def main(csv_file: Path, dry_run: bool, limit: int | None):
    """Upload fake Linear issues from CSV file for testing purposes."""
    click.echo("=" * 60)
    click.echo("Fake Linear Issue Upload Script")
    click.echo("=" * 60)

    # Load configuration
    try:
        config = get_config()
        if not config.linear.linear_api_key:
            click.echo(
                "\nError: Linear configuration not found. Please run 'whatdidido init' first.",
                err=True,
            )
            sys.exit(1)
        api_key = config.linear.linear_api_key
    except Exception as e:
        click.echo(f"\nError loading configuration: {e}", err=True)
        sys.exit(1)

    # Test connection
    if not dry_run:
        try:
            click.echo("\nTesting Linear API connection...")
            query = """
            query {
                viewer {
                    id
                    name
                    email
                }
            }
            """
            result = make_graphql_request(api_key, query)
            viewer = result.get("data", {}).get("viewer", {})
            click.echo(
                f"Connected as: {viewer.get('name')} ({viewer.get('email')})"
            )
        except Exception as e:
            click.echo(f"\nError connecting to Linear: {e}", err=True)
            sys.exit(1)
    else:
        click.echo("\n[DRY RUN MODE] - No actual changes will be made")

    # Read CSV file
    click.echo(f"\nReading issues from: {csv_file}")
    try:
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except Exception as e:
        click.echo(f"\nError reading CSV file: {e}", err=True)
        sys.exit(1)

    if not rows:
        click.echo("\nNo issues found in CSV file", err=True)
        sys.exit(1)

    # Get team ID from first row
    team_key = rows[0]["team_key"]
    click.echo(f"\nGetting team ID for: {team_key}")

    try:
        team_id = get_or_create_team(api_key, team_key)
        click.echo(f"Team ID: {team_id}")
    except Exception as e:
        click.echo(f"\nError: {e}", err=True)
        sys.exit(1)

    # Apply limit if specified
    if limit:
        rows = rows[:limit]
        click.echo(f"Limited to first {limit} issues")

    click.echo(f"\nTotal issues to create: {len(rows)}")

    # Confirm before proceeding
    if not dry_run:
        if not click.confirm(
            "\nThis will create issues in your Linear workspace. Continue?"
        ):
            click.echo("Aborted.")
            sys.exit(0)

    # Create issues
    created_count = 0
    failed_count = 0

    for i, row in enumerate(rows, 1):
        click.echo(f"\n[{i}/{len(rows)}]", nl="")
        result = create_linear_issue(api_key, row, team_id, dry_run)
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
        click.echo(f"Would have created: {len(rows)} issues")
    else:
        click.echo(f"Successfully created: {created_count} issues")
        if failed_count > 0:
            click.echo(f"Failed: {failed_count} issues")
        click.echo(f"\nView your issues at: https://linear.app/team/{team_key}/")


if __name__ == "__main__":
    main()
