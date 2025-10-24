import datetime
import json
from typing import Any, Generator, TypedDict

import questionary
import requests

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


class LinearProvider(BaseProvider):
    def get_name(self) -> str:
        return "Linear"

    def is_configured(self) -> bool:
        config = get_config()
        return config.linear.linear_api_key != ""

    def setup(self):
        is_configured = self.is_configured()
        confirm_configured = False
        if is_configured:
            confirm_configured = questionary.confirm(
                "Linear is already configured. Do you want to reconfigure it?",
                default=False,
            ).ask()
        if not is_configured or confirm_configured:
            credentials = ask_linear_credentials()
            update_config("LINEAR_API_KEY", credentials["api_key"])

        if self.authenticate():
            logger.info("Linear has been successfully configured.")

    def authenticate(self) -> bool:
        config = get_config()
        try:
            self.api_key = config.linear.linear_api_key
            self.graphql_url = "https://api.linear.app/graphql"

            # Test authentication with a simple query
            query = """
            query {
                viewer {
                    id
                    name
                    email
                }
            }
            """
            self._make_graphql_request(query)
            return True
        except Exception as e:
            logger.error(f"Failed to authenticate with Linear: {e}")
            return False

    def _make_graphql_request(self, query: str, variables: dict | None = None) -> dict:
        """Make a GraphQL request to Linear API."""
        headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
        }

        payload: dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables

        try:
            response = requests.post(self.graphql_url, json=payload, headers=headers)

            # Log response body
            try:
                response.json()
            except Exception as json_error:
                logger.error(f"Response Body (raw): {response.text[:1000]}")
                logger.error(f"JSON parsing error: {json_error}")

            # Raise for HTTP errors (will include response body in error)
            response.raise_for_status()

            result = response.json()
            if "errors" in result:
                logger.error("\n=== GraphQL Errors Detected ===")
                logger.error(f"Errors: {json.dumps(result['errors'], indent=2)}")
                raise Exception(f"GraphQL errors: {result['errors']}")

            return result

        except requests.exceptions.HTTPError as http_err:
            logger.error("\n=== HTTP Error ===")
            logger.error(f"HTTP Error: {http_err}")
            logger.error(f"Response Text: {response.text}")
            raise
        except requests.exceptions.RequestException as req_err:
            logger.error("\n=== Request Error ===")
            logger.error(f"Request Error: {req_err}")
            raise
        except Exception as e:
            logger.error("\n=== Unexpected Error ===")
            logger.error(f"Error: {e}")
            raise

    def fetch_items(self, params: FetchParams) -> Generator[WorkItem, None, None]:
        """
        Fetch Linear issues updated within the date range.

        Args:
            params: FetchParams object containing filtering options

        Yields:
            WorkItem objects with comprehensive Linear data
        """
        if not hasattr(self, "api_key") or self.api_key is None:
            if not self.authenticate():
                return

        # Convert dates to ISO strings for Linear API
        start_date_str = params.start_date.isoformat()
        end_date_str = (params.end_date + datetime.timedelta(days=1)).isoformat()

        logger.info(f"Fetching Linear issues from {start_date_str} to {end_date_str}")

        # Get user ID for filtering
        if params.user_filter:
            # Try to find user by email
            user_query = """
            query($email: String!) {
                users(filter: { email: { eq: $email } }) {
                    nodes {
                        id
                        email
                        name
                    }
                }
            }
            """
            user_response = self._make_graphql_request(
                user_query, {"email": params.user_filter}
            )
            users = user_response.get("data", {}).get("users", {}).get("nodes", [])

            if not users:
                logger.warning(
                    f"Warning: No user found with email '{params.user_filter}'. Fetching issues anyway."
                )
                user_id = None
            else:
                user_id = users[0]["id"]
                user_name = users[0].get("name", params.user_filter)
                logger.info(
                    f"Fetching issues for user: {user_name} ({params.user_filter})"
                )
        else:
            # Get current user's ID
            viewer_query = """
            query {
                viewer {
                    id
                }
            }
            """
            viewer_response = self._make_graphql_request(viewer_query)
            user_id = viewer_response.get("data", {}).get("viewer", {}).get("id")
        # Fetch issues with pagination
        has_next_page = True
        end_cursor = None
        total_fetched = 0

        while has_next_page:
            try:

                # Build the GraphQL query with pagination
                query = """
                query($after: String, $startDate: DateTimeOrDuration!, $endDate: DateTimeOrDuration!, $userId: ID!) {
                    issues(
                        first: 50
                        after: $after
                        filter: {
                            updatedAt: { gte: $startDate, lte: $endDate }
                            or: [
                                { assignee: { id: { eq: $userId } } }
                                { creator: { id: { eq: $userId } } }
                            ]
                        }
                        orderBy: updatedAt
                    ) {
                        pageInfo {
                            hasNextPage
                            endCursor
                        }
                        nodes {
                            id
                            identifier
                            title
                            description
                            url
                            createdAt
                            updatedAt
                            archivedAt
                            state {
                                id
                                name
                                type
                                color
                            }
                            priority
                            priorityLabel
                            estimate
                            assignee {
                                id
                                name
                                email
                                displayName
                            }
                            creator {
                                id
                                name
                                email
                                displayName
                            }
                            project {
                                id
                                name
                                description
                                state
                                targetDate
                            }
                            team {
                                id
                                name
                                key
                            }
                            cycle {
                                id
                                number
                                name
                                startsAt
                                endsAt
                            }
                            labels {
                                nodes {
                                    id
                                    name
                                    color
                                }
                            }
                            parent {
                                id
                                identifier
                                title
                            }
                            children {
                                nodes {
                                    id
                                    identifier
                                    title
                                }
                            }
                            comments {
                                nodes {
                                    id
                                    body
                                    createdAt
                                    updatedAt
                                    user {
                                        id
                                        name
                                        email
                                        displayName
                                    }
                                }
                            }
                        }
                    }
                }
                """

                variables = {
                    "after": end_cursor,
                    "startDate": start_date_str,
                    "endDate": end_date_str,
                    "userId": user_id,
                }

                response = self._make_graphql_request(query, variables)
                issues_data = response.get("data", {}).get("issues", {})

                page_info = issues_data.get("pageInfo", {})
                has_next_page = page_info.get("hasNextPage", False)
                end_cursor = page_info.get("endCursor")

                issues = issues_data.get("nodes", [])

                for issue in issues:
                    work_item = self._convert_linear_issue_to_work_item(issue)
                    total_fetched += 1
                    yield work_item

            except Exception as e:
                logger.error(f"Error fetching Linear issues: {e}")
                break

    def _convert_linear_issue_to_work_item(self, issue: dict[str, Any]) -> WorkItem:
        """
        Convert a Linear issue to a WorkItem with all available context.

        All Linear-specific fields are stored in raw_data for extensibility.

        Args:
            issue: Linear issue object (dict from GraphQL response)

        Returns:
            WorkItem with core fields and Linear-specific data in raw_data
        """

        # Helper function to safely get nested values
        def safe_get(obj, *keys, default=None):
            for key in keys:
                if obj is None:
                    return default
                if isinstance(obj, dict):
                    obj = obj.get(key)
                else:
                    return default
            return obj if obj is not None else default

        # Helper to convert user object to dict
        def user_to_dict(user_obj):
            if user_obj is None:
                return None
            return {
                "id": safe_get(user_obj, "id"),
                "name": safe_get(user_obj, "name"),
                "display_name": safe_get(user_obj, "displayName"),
                "email": safe_get(user_obj, "email"),
            }

        # Extract state information
        state_data = None
        if issue.get("state"):
            state = issue["state"]
            state_data = {
                "id": safe_get(state, "id"),
                "name": safe_get(state, "name"),
                "type": safe_get(state, "type"),
                "color": safe_get(state, "color"),
            }

        # Extract project information
        project_data = None
        if issue.get("project"):
            project = issue["project"]
            project_data = {
                "id": safe_get(project, "id"),
                "name": safe_get(project, "name"),
                "description": safe_get(project, "description"),
                "state": safe_get(project, "state"),
                "target_date": safe_get(project, "targetDate"),
            }

        # Extract team information
        team_data = None
        if issue.get("team"):
            team = issue["team"]
            team_data = {
                "id": safe_get(team, "id"),
                "name": safe_get(team, "name"),
                "key": safe_get(team, "key"),
            }

        # Extract cycle information (similar to sprint)
        cycle_data = None
        if issue.get("cycle"):
            cycle = issue["cycle"]
            cycle_data = {
                "id": safe_get(cycle, "id"),
                "number": safe_get(cycle, "number"),
                "name": safe_get(cycle, "name"),
                "starts_at": safe_get(cycle, "startsAt"),
                "ends_at": safe_get(cycle, "endsAt"),
            }

        # Extract labels
        labels = []
        if issue.get("labels"):
            label_nodes = safe_get(issue, "labels", "nodes", default=[])
            labels = [
                {
                    "id": label.get("id"),
                    "name": label.get("name"),
                    "color": label.get("color"),
                }
                for label in label_nodes
            ]

        # Extract parent (for sub-issues)
        parent_data = None
        if issue.get("parent"):
            parent = issue["parent"]
            parent_data = {
                "id": safe_get(parent, "id"),
                "identifier": safe_get(parent, "identifier"),
                "title": safe_get(parent, "title"),
            }

        # Extract children (sub-issues)
        children = []
        if issue.get("children"):
            children_nodes = safe_get(issue, "children", "nodes", default=[])
            children = [
                {
                    "id": child.get("id"),
                    "identifier": child.get("identifier"),
                    "title": child.get("title"),
                }
                for child in children_nodes
            ]

        # Extract comments
        comments_data: CommentData = {
            "count": 0,
            "last_comment_at": None,
            "last_comment_author": None,
            "comments": [],
        }
        if issue.get("comments"):
            comment_nodes = safe_get(issue, "comments", "nodes", default=[])
            comments_data["count"] = len(comment_nodes)

            for comment in comment_nodes:
                comments_data["comments"].append(
                    {
                        "id": safe_get(comment, "id"),
                        "body": safe_get(comment, "body"),
                        "created_at": safe_get(comment, "createdAt"),
                        "updated_at": safe_get(comment, "updatedAt"),
                        "user": user_to_dict(safe_get(comment, "user")),
                    }
                )

            if comment_nodes:
                last_comment = comment_nodes[-1]
                comments_data["last_comment_at"] = safe_get(last_comment, "createdAt")
                comments_data["last_comment_author"] = safe_get(
                    last_comment, "user", "displayName"
                ) or safe_get(last_comment, "user", "name")

        # Build raw_data with all Linear-specific information
        raw_data = {
            # Status and type
            "state": state_data,
            "priority": safe_get(issue, "priority"),
            "priority_label": safe_get(issue, "priorityLabel"),
            # People
            "assignee": user_to_dict(safe_get(issue, "assignee")),
            "creator": user_to_dict(safe_get(issue, "creator")),
            # Project context
            "project": project_data,
            "team": team_data,
            # Categorization
            "labels": labels,
            # Cycle/iteration info (similar to sprint)
            "cycle": cycle_data,
            # Estimate (similar to story points)
            "estimate": safe_get(issue, "estimate"),
            # Relationships
            "parent": parent_data,
            "children": children,
            # Comments and activity
            "comments": comments_data,
            # Additional metadata
            "archived_at": safe_get(issue, "archivedAt"),
        }

        # Build the work item with core fields only
        work_item = WorkItem(
            id=safe_get(issue, "identifier", default=""),
            title=safe_get(issue, "title", default="No title"),
            description=safe_get(issue, "description", default=""),
            url=safe_get(issue, "url", default=""),
            created_at=safe_get(issue, "createdAt", default=""),
            updated_at=safe_get(issue, "updatedAt", default=""),
            provider="Linear",
            raw_data=raw_data,
        )

        return work_item

    def disconnect(self):
        """Remove Linear configuration (credentials and settings)."""
        update_config("LINEAR_API_KEY", "")


def ask_linear_credentials():
    linear_api_key = questionary.password(
        "Enter your Linear API key (get it from https://linear.app/settings/api):"
    ).ask()

    return {
        "api_key": linear_api_key,
    }
