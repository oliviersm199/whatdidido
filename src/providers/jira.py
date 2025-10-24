from typing import Generator, TypedDict

import jira
import questionary

from config import get_config, update_config
from logger import get_logger
from models.fetch_params import FetchParams
from models.work_item import WorkItem
from providers.base import BaseProvider

logger = get_logger(__name__)


class CommentData(TypedDict):
    count: int
    last_comment_at: str | None
    last_comment_author: str | None
    comments: list[dict[str, str | dict | None]]


class JiraProvider(BaseProvider):
    def get_name(self) -> str:
        return "Jira"

    def is_configured(self) -> bool:
        config = get_config()
        return (
            config.jira.jira_url != ""
            and config.jira.jira_username != ""
            and config.jira.jira_api_key != ""
        )

    def setup(self):
        is_configured = self.is_configured()
        confirm_configured = False
        if is_configured:
            confirm_configured = questionary.confirm(
                "Jira is already configured. Do you want to reconfigure it?",
                default=False,
            ).ask()
        if not is_configured or confirm_configured:
            credentials = ask_jira_credentials()
            update_config("JIRA_URL", credentials["server"])
            update_config("JIRA_USERNAME", credentials["username"])
            update_config("JIRA_API_KEY", credentials["api_token"])

        if self.authenticate():
            logger.info("Jira has been successfully configured.")

    def authenticate(self) -> bool:
        config = get_config()
        try:
            self.jira_client = jira.JIRA(
                server=config.jira.jira_url,
                basic_auth=(config.jira.jira_username, config.jira.jira_api_key),
                timeout=25,
            )
            server_info = self.jira_client.server_info()
            logger.info(f"Connected to Jira server version: {server_info['version']}")
            return True
        except jira.JIRAError as e:
            logger.error(f"Failed to authenticate with Jira: {e}")
            return False
        except Exception as e:
            # Catch timeout and other connection errors
            logger.error(f"Failed to connect to Jira: {e}")
            return False

    def fetch_items(self, params: FetchParams) -> Generator[WorkItem, None, None]:
        """
        Fetch Jira issues updated within the date range.

        Args:
            params: FetchParams object containing filtering options

        Yields:
            WorkItem objects with comprehensive Jira data
        """
        if not hasattr(self, "jira_client") or self.jira_client is None:
            if not self.authenticate():
                return

        # Build JQL query
        jql_parts = []

        # Convert dates to strings for JQL query
        start_date_str = params.start_date.strftime("%Y-%m-%d")
        end_date_str = params.end_date.strftime("%Y-%m-%d")

        jql_parts.append(
            f'updated >= "{start_date_str}" AND updated <= "{end_date_str}"'
        )

        # Build user filter
        if params.user_filter:
            # Support email or username
            user_identifier = params.user_filter
            jql_parts.append(
                f'(assignee = "{user_identifier}" OR reporter = "{user_identifier}") ORDER BY updated DESC'
            )
        else:
            # Get issues assigned to current user or where user is reporter
            jql_parts.append(
                "(assignee = currentUser() OR reporter = currentUser()) ORDER BY updated DESC"
            )

        jql_query = " AND ".join(jql_parts)

        logger.debug(f"JQL Query: {jql_query}")

        # Fetch issues with pagination
        start_at = 0
        max_results = 50
        total_fetched = 0

        while True:
            try:
                issues = self.jira_client.search_issues(
                    jql_query,
                    startAt=start_at,
                    maxResults=max_results,
                    expand="changelog",  # Include change history for more context
                )

                if not issues:
                    break

                for issue in issues:
                    work_item = self._convert_jira_issue_to_work_item(issue)
                    total_fetched += 1
                    yield work_item

                # Check if we've fetched all issues
                if len(issues) < max_results:
                    break

                start_at += max_results

            except jira.JIRAError as e:
                logger.error(f"Error fetching Jira issues: {e}")
                break

        logger.info(f"Fetched {total_fetched} issues from Jira")

    def _convert_jira_issue_to_work_item(self, issue) -> WorkItem:
        """
        Convert a Jira issue to a WorkItem with all available context.

        All Jira-specific fields are stored in raw_data for extensibility.

        Args:
            issue: Jira issue object

        Returns:
            WorkItem with core fields and Jira-specific data in raw_data
        """
        fields = issue.fields

        # Helper function to safely get attribute
        def safe_get(obj, attr, default=None):
            try:
                val = getattr(obj, attr, default)
                return val if val is not None else default
            except Exception:
                return default

        # Helper to get display name from user object
        def get_user_name(user_obj):
            if user_obj is None:
                return None
            return safe_get(user_obj, "displayName") or safe_get(user_obj, "name")

        # Helper to convert user object to dict
        def user_to_dict(user_obj):
            if user_obj is None:
                return None
            return {
                "name": safe_get(user_obj, "name"),
                "display_name": safe_get(user_obj, "displayName"),
                "email": safe_get(user_obj, "emailAddress"),
            }

        # Extract sprint information
        sprint_data = None
        if hasattr(fields, "customfield_10020"):  # Common sprint field ID
            sprints = safe_get(fields, "customfield_10020", [])
            if sprints and isinstance(sprints, list) and len(sprints) > 0:
                # Get the most recent sprint
                latest_sprint = sprints[-1]
                if hasattr(latest_sprint, "name"):
                    sprint_data = {
                        "id": str(safe_get(latest_sprint, "id", "")),
                        "name": latest_sprint.name,
                        "state": safe_get(latest_sprint, "state"),
                        "start_date": safe_get(latest_sprint, "startDate"),
                        "end_date": safe_get(latest_sprint, "endDate"),
                    }

        # Extract story points
        story_points = None
        if hasattr(fields, "customfield_10016"):  # Common story points field
            story_points = safe_get(fields, "customfield_10016")

        # Extract subtasks
        subtasks = []
        if hasattr(fields, "subtasks") and fields.subtasks:
            subtasks = [
                {
                    "key": str(subtask.key),
                    "summary": safe_get(subtask.fields, "summary"),
                }
                for subtask in fields.subtasks
            ]

        # Extract parent (for subtasks)
        parent_data = None
        if hasattr(fields, "parent") and fields.parent:
            parent_data = {
                "key": str(fields.parent.key),
                "summary": safe_get(fields.parent.fields, "summary"),
            }

        # Extract labels
        labels = []
        if hasattr(fields, "labels") and fields.labels:
            labels = list(fields.labels)

        # Extract components
        components = []
        if hasattr(fields, "components") and fields.components:
            components = [comp.name for comp in fields.components]

        # Time tracking
        time_tracking_data = None
        if hasattr(fields, "timetracking") and fields.timetracking:
            time_tracking = fields.timetracking
            time_tracking_data = {
                "original_estimate_seconds": safe_get(
                    time_tracking, "originalEstimateSeconds"
                ),
                "time_spent_seconds": safe_get(time_tracking, "timeSpentSeconds"),
                "remaining_estimate_seconds": safe_get(
                    time_tracking, "remainingEstimateSeconds"
                ),
            }

        # Comments
        comments_data: CommentData = {
            "count": 0,
            "last_comment_at": None,
            "last_comment_author": None,
            "comments": [],
        }
        if hasattr(fields, "comment") and fields.comment:
            raw_comments = safe_get(fields.comment, "comments", [])
            comments_data["count"] = len(raw_comments)

            # Extract all comment details
            for comment in raw_comments:
                comments_data["comments"].append(
                    {
                        "id": safe_get(comment, "id"),
                        "author": user_to_dict(safe_get(comment, "author")),
                        "body": safe_get(comment, "body"),
                        "created": safe_get(comment, "created"),
                        "updated": safe_get(comment, "updated"),
                    }
                )

            if raw_comments:
                last_comment = raw_comments[-1]
                comments_data["last_comment_at"] = safe_get(last_comment, "created")
                comments_data["last_comment_author"] = get_user_name(
                    safe_get(last_comment, "author")
                )

        # Build raw_data with all Jira-specific information
        raw_data = {
            # Status and type
            "status": safe_get(fields.status, "name", "Unknown"),
            "status_category": (
                safe_get(safe_get(fields.status, "statusCategory"), "name")
                if hasattr(fields, "status") and fields.status
                else None
            ),
            "issue_type": safe_get(fields.issuetype, "name", "Unknown"),
            "priority": (
                safe_get(fields.priority, "name")
                if hasattr(fields, "priority") and fields.priority
                else None
            ),
            # People
            "assignee": user_to_dict(safe_get(fields, "assignee")),
            "reporter": user_to_dict(safe_get(fields, "reporter")),
            "creator": user_to_dict(safe_get(fields, "creator")),
            # Project context
            "project": {
                "key": (
                    safe_get(fields.project, "key")
                    if hasattr(fields, "project")
                    else None
                ),
                "name": (
                    safe_get(fields.project, "name")
                    if hasattr(fields, "project")
                    else None
                ),
            },
            # Categorization
            "labels": labels,
            "components": components,
            # Sprint/iteration info
            "sprint": sprint_data,
            # Time tracking
            "time_tracking": time_tracking_data,
            # Story points
            "story_points": story_points,
            # Relationships
            "parent": parent_data,
            "epic_link": (
                safe_get(fields, "customfield_10014")
                if hasattr(fields, "customfield_10014")
                else None
            ),
            "subtasks": subtasks,
            # Comments and activity
            "comments": comments_data,
            # Additional metadata
            "resolution": (
                safe_get(fields.resolution, "name")
                if hasattr(fields, "resolution") and fields.resolution
                else None
            ),
            "resolved_at": safe_get(fields, "resolutiondate"),
            "environment": safe_get(fields, "environment"),
        }

        # Build the work item with core fields only
        work_item = WorkItem(
            id=str(issue.key),
            title=safe_get(fields, "summary", "No title"),
            description=safe_get(fields, "description", ""),
            url=f"{self.jira_client.server_url}/browse/{issue.key}",
            created_at=safe_get(fields, "created", ""),
            updated_at=safe_get(fields, "updated", ""),
            provider="Jira",
            raw_data=raw_data,
        )

        return work_item

    def disconnect(self):
        """Remove Jira configuration (credentials and settings)."""
        update_config("JIRA_URL", "")
        update_config("JIRA_USERNAME", "")
        update_config("JIRA_API_KEY", "")


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
