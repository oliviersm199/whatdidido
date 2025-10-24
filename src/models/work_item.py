from typing import Any

from pydantic import BaseModel, Field


class WorkItem(BaseModel):
    """
    Represents a work item from any provider (Jira, Linear, etc.).

    This model is intentionally minimal and provider-agnostic. Only core fields
    that exist across all work tracking systems are included. Provider-specific
    data should be stored in the raw_data field.
    """

    # Core identification
    id: str = Field(description="Unique identifier (e.g., PROJ-123, ISSUE-456)")
    title: str = Field(description="Summary/title of the work item")
    description: str | None = Field(
        default=None, description="Full description/body of the work item"
    )
    url: str = Field(description="Direct link to the work item")

    # Timestamps
    created_at: str = Field(description="When the item was created (ISO 8601)")
    updated_at: str = Field(description="When the item was last updated (ISO 8601)")

    # Provider information
    provider: str = Field(description="Source provider (e.g., Jira, Linear)")

    # Provider-specific data
    raw_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Provider-specific data (status, assignee, labels, etc.)",
    )
