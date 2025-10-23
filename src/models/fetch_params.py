from datetime import date

from pydantic import BaseModel, Field


class FetchParams(BaseModel):
    """
    Parameters for fetching work items from a provider.

    This model encapsulates all the filtering and configuration options
    for fetching work items, making it easier to extend in the future.
    """

    start_date: date = Field(description="Start date for fetching items")
    end_date: date = Field(description="End date for fetching items")
    user_filter: str | None = Field(
        default=None,
        description=(
            "Optional user identifier (email, username, or ID). "
            "If None, fetches items for the authenticated user. "
            "Format depends on the provider (e.g., email for Jira/Linear)."
        ),
    )
