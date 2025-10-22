"""
Summarizes work items through a 3 step flow:

1. Iterates through each work item and uses a low cost LLM to generate a concise 3-4 sentence summary.
2. Aggregates these summaries into a single text blob.
3. Uses a more capable LLM to generate an overall summary of the aggregated text.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

from filelock import FileLock
from openai import OpenAI
from pydantic import BaseModel, Field

from config import get_config
from models.work_item import WorkItem

WORK_ITEM_SUMMARY_PROMPT = """
You are an expert at summarizing technical work items into concise, clear summaries.
Given the following work item, generate a concise summary in 3-4 sentences, focusing on the key aspects and outcomes.
DO NOT include any personal opinions or extraneous information. DO NOT INVENT ANY DETAILS OUTSIDE OF THE PROVIDED DATA.

Work Item Data:
{work_item_data}

Provide only the summary text, no additional formatting or preamble.
"""

OVERALL_SUMMARY_PROMPT = """
You are an expert at synthesizing multiple technical work item summaries into a coherent overall summary.
Given the following aggregated summaries of work items, generate a clear and well-structured overall summary in markdown format that captures the main themes and outcomes.

The summary should:
- Start with a high-level overview of the work completed
- Group related work items into logical categories
- Highlight key achievements and outcomes
- Be formatted in markdown with appropriate headers and bullet points
- Focus on the key aspects and avoid unnecessary details

Work Item Summaries:
{summaries}

Provide the complete markdown summary, ready to be saved to a file.
"""

SUMMARY_FILE = "whatdidido-summary.json"
SUMMARY_LOCK = ".whatdidido-summary.json.lock"
MARKDOWN_FILE = "whatdidido.md"


class WorkItemSummary(BaseModel):
    """Represents a summary of a single work item."""

    work_item_id: str = Field(description="ID of the work item")
    title: str = Field(description="Title of the work item")
    summary: str = Field(description="Generated summary text")
    provider: str = Field(description="Source provider")
    created_at: str = Field(description="When the work item was created")
    updated_at: str = Field(description="When the work item was last updated")
    summarized_at: str = Field(description="When this summary was generated (ISO 8601)")


class WorkItemSummarizer:
    """
    Takes a list of work items and generates summaries for each one.
    Persists the summaries to whatdidido-summary.json.
    """

    def __init__(self, summary_file: Path | None = None):
        """
        Initialize the WorkItemSummarizer.

        Args:
            summary_file: Path to the summary JSON file. If None, uses default.
        """
        self.config = get_config()
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.config.openrouter.openrouter_api_key,
        )
        self.summary_file = summary_file or Path(SUMMARY_FILE)
        self.lock_file = Path(SUMMARY_LOCK)
        self._ensure_summary_file_exists()

    def _ensure_summary_file_exists(self) -> None:
        """Create the summary file with empty structure if it doesn't exist."""
        if not self.summary_file.exists():
            self.summary_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.summary_file, "w") as f:
                json.dump([], f)

    def _get_lock(self) -> FileLock:
        """Get a file lock for thread-safe operations."""
        return FileLock(str(self.lock_file), timeout=10)

    def _read_summaries(self) -> list[WorkItemSummary]:
        """Read all summaries from the JSON file."""
        with self._get_lock():
            with open(self.summary_file, "r") as f:
                data = json.load(f)
                return [WorkItemSummary(**item) for item in data]

    def _write_summaries(self, summaries: list[WorkItemSummary]) -> None:
        """Write summaries to the JSON file atomically."""
        temp_file = self.summary_file.with_suffix(self.summary_file.suffix + ".tmp")
        with open(temp_file, "w") as f:
            json.dump(
                [summary.model_dump() for summary in summaries],
                f,
                indent=2,
                sort_keys=True,
            )
        temp_file.replace(self.summary_file)

    def _generate_summary(self, work_item: WorkItem) -> str:
        """
        Generate a summary for a single work item using the LLM.

        Args:
            work_item: The work item to summarize

        Returns:
            The generated summary text
        """
        # Format raw_data for better readability
        raw_data_str = json.dumps(work_item.raw_data, indent=2)

        # Format work item data for the prompt
        work_item_data = f"""
ID: {work_item.id}
Title: {work_item.title}
Description: {work_item.description or "N/A"}
URL: {work_item.url}
Created: {work_item.created_at}
Updated: {work_item.updated_at}
Provider: {work_item.provider}

Raw Provider Data:
{raw_data_str}
"""

        prompt = WORK_ITEM_SUMMARY_PROMPT.format(work_item_data=work_item_data)

        response = self.client.chat.completions.create(
            model=self.config.openrouter.openrouter_workitem_summary_model,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.choices[0].message.content.strip()

    def summarize_work_items(self, work_items: list[WorkItem]) -> list[WorkItemSummary]:
        """
        Generate summaries for a list of work items and persist them.

        Args:
            work_items: List of work items to summarize

        Returns:
            List of generated summaries

        Example:
            summarizer = WorkItemSummarizer()
            summaries = summarizer.summarize_work_items(work_items)
        """
        summaries: list[WorkItemSummary] = []

        for work_item in work_items:
            print(f"Summarizing {work_item.id}: {work_item.title}...", file=sys.stderr)
            summary_text = self._generate_summary(work_item)

            summary = WorkItemSummary(
                work_item_id=work_item.id,
                title=work_item.title,
                summary=summary_text,
                provider=work_item.provider,
                created_at=work_item.created_at,
                updated_at=work_item.updated_at,
                summarized_at=datetime.now().isoformat(),
            )
            summaries.append(summary)

        # Persist all summaries
        with self._get_lock():
            self._write_summaries(summaries)

        return summaries

    def get_summaries(self) -> list[WorkItemSummary]:
        """
        Get all stored summaries.

        Returns:
            List of all work item summaries
        """
        return self._read_summaries()


class OverallSummarizer:
    """
    Takes work item summaries and produces a global summary.
    Prints to stdout and saves as whatdidido.md.
    """

    def __init__(self, markdown_file: Path | None = None):
        """
        Initialize the OverallSummarizer.

        Args:
            markdown_file: Path to the markdown output file. If None, uses default.
        """
        self.config = get_config()
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.config.openrouter.openrouter_api_key,
        )
        self.markdown_file = markdown_file or Path(MARKDOWN_FILE)

    def _format_summaries_for_prompt(self, summaries: list[WorkItemSummary]) -> str:
        """Format summaries into a text blob for the LLM."""
        formatted = []
        for summary in summaries:
            formatted.append(
                f"- **{summary.work_item_id}** ({summary.provider}): {summary.title}\n"
                f"  {summary.summary}\n"
                f"  Created: {summary.created_at} | Updated: {summary.updated_at}\n"
            )
        return "\n".join(formatted)

    def _generate_overall_summary(self, summaries: list[WorkItemSummary]) -> str:
        """
        Generate an overall summary from work item summaries.

        Args:
            summaries: List of work item summaries

        Returns:
            The generated markdown summary
        """
        summaries_text = self._format_summaries_for_prompt(summaries)
        prompt = OVERALL_SUMMARY_PROMPT.format(summaries=summaries_text)

        response = self.client.chat.completions.create(
            model=self.config.openrouter.openrouter_summary_model,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.choices[0].message.content.strip()

    def generate_and_save_summary(self, summaries: list[WorkItemSummary]) -> str:
        """
        Generate an overall summary, print it to stdout, and save to markdown file.

        Args:
            summaries: List of work item summaries to aggregate

        Returns:
            The generated markdown summary

        Example:
            overall = OverallSummarizer()
            markdown = overall.generate_and_save_summary(summaries)
        """
        markdown_summary = self._generate_overall_summary(summaries)

        # Save to file
        self.markdown_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.markdown_file, "w") as f:
            f.write(markdown_summary)

        # Print to stdout
        print(markdown_summary)

        return markdown_summary
