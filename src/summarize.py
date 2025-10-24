"""
Summarizes work items through a 3 step flow:

1. Iterates through each work item and uses a low cost LLM to generate a concise 3-4 sentence summary.
2. Aggregates these summaries into a single text blob.
3. Uses a more capable LLM to generate an overall summary of the aggregated text.
"""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import tiktoken
from filelock import FileLock
from openai import OpenAI
from pydantic import BaseModel, Field
from rich.console import Console
from rich.markdown import Markdown
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)

from config import get_config
from logger import get_logger
from models.work_item import WorkItem
from utils.lock_utils import with_lock_cleanup

logger = get_logger(__name__)

WORK_ITEM_SUMMARY_PROMPT = """
You are helping a software engineer prepare for their performance review by summarizing their work.

Given the work item below, create a 3-4 sentence summary that:
- Highlights the technical problem solved or feature delivered
- Notes the impact or outcome (e.g., improved performance, enabled new capability, fixed critical bug)
- Mentions any collaboration, leadership, or technical complexity involved
- Uses active voice focused on what the engineer accomplished

Work Item Data:
{work_item_data}

Write only the summary - no preamble, bullet points, or additional commentary.
"""

OVERALL_SUMMARY_PROMPT = """
You are helping a software engineer craft their performance review self-evaluation.

Using the work item summaries below, create a cohesive narrative in markdown that:

**Structure:**
- Begin with a brief overview highlighting 2-3 major themes or accomplishments
- Group related work into 4-6 meaningful categories (e.g., "Infrastructure & Performance",
"Feature Development", "Technical Leadership", "Bug Fixes & Maintenance")
- Within each category, synthesize the work rather than listing items individually
- End with a brief reflection on growth areas or skills demonstrated

**Content guidelines:**
- Emphasize impact and outcomes over tasks
- Highlight technical complexity, leadership, or collaboration where evident
- Use specific metrics or outcomes when mentioned in the summaries
- Maintain a professional but confident tone appropriate for self-evaluation
- Keep each category concise (3-5 sentences)

Work Item Summaries:
{summaries}

Generate the complete markdown summary.
"""

SUMMARY_FILE = "whatdidido-summary.json"
SUMMARY_LOCK = "whatdidido-summary.json.lock"  # Lock file without leading dot
MARKDOWN_FILE = "whatdidido.md"


class ContextWindowExceededError(Exception):
    """Raised when the prompt exceeds the model's context window."""

    pass


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
            base_url=self.config.openai.openai_base_url,
            api_key=self.config.openai.openai_api_key,
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

    @with_lock_cleanup(SUMMARY_LOCK)
    def _read_summaries(self) -> list[WorkItemSummary]:
        """Read all summaries from the JSON file."""
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
            model=self.config.openai.openai_workitem_summary_model,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.choices[0].message.content.strip()

    def _summarize_single_work_item(self, work_item: WorkItem) -> WorkItemSummary:
        """
        Generate a summary for a single work item.

        Args:
            work_item: The work item to summarize

        Returns:
            WorkItemSummary with the generated summary
        """
        summary_text = self._generate_summary(work_item)

        return WorkItemSummary(
            work_item_id=work_item.id,
            title=work_item.title,
            summary=summary_text,
            provider=work_item.provider,
            created_at=work_item.created_at,
            updated_at=work_item.updated_at,
            summarized_at=datetime.now().isoformat(),
        )

    def summarize_work_items(self, work_items: list[WorkItem]) -> list[WorkItemSummary]:
        """
        Generate summaries for a list of work items and persist them.
        Uses parallel processing with a ThreadPool (max 4 workers) for improved performance.

        Args:
            work_items: List of work items to summarize

        Returns:
            List of generated summaries

        Example:
            summarizer = WorkItemSummarizer()
            summaries = summarizer.summarize_work_items(work_items)
        """
        summaries: list[WorkItemSummary] = []

        # Track which work items are currently being processed
        in_progress: set[str] = set()

        # Create a progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
        ) as progress:
            task = progress.add_task("Summarizing work items...", total=len(work_items))

            # Use ThreadPoolExecutor with max 4 workers for parallel summarization
            with ThreadPoolExecutor(max_workers=4) as executor:
                # Submit all summarization tasks
                future_to_work_item = {
                    executor.submit(
                        self._summarize_single_work_item, work_item
                    ): work_item
                    for work_item in work_items
                }

                # Track which futures are running
                for work_item in work_items[:4]:  # Initial batch
                    in_progress.add(f"{work_item.id}: {work_item.title}")

                # Collect results as they complete
                completed_count = 0
                for future in as_completed(future_to_work_item):
                    try:
                        summary = future.result()
                        summaries.append(summary)
                        completed_count += 1

                        # Remove completed item from in_progress
                        completed_work_item = future_to_work_item[future]
                        completed_id = (
                            f"{completed_work_item.id}: {completed_work_item.title}"
                        )
                        in_progress.discard(completed_id)

                        # Add next item to in_progress if there are more
                        if completed_count + len(in_progress) < len(work_items):
                            next_idx = completed_count + len(in_progress) - 1
                            if next_idx < len(work_items):
                                next_item = work_items[next_idx]
                                in_progress.add(f"{next_item.id}: {next_item.title}")

                        # Update progress description with current items
                        description = (
                            f"Summarizing: {', '.join(sorted(list(in_progress)[:4]))}"
                        )
                        if len(in_progress) > 4:
                            description += "..."
                        progress.update(task, description=description, advance=1)

                    except Exception as e:
                        work_item = future_to_work_item[future]
                        progress.stop()
                        logger.error(f"Error summarizing {work_item.id}: {str(e)}")
                        raise

        # Persist all summaries
        self._persist_summaries(summaries)

        return summaries

    @with_lock_cleanup(SUMMARY_LOCK)
    def _persist_summaries(self, summaries: list[WorkItemSummary]) -> None:
        """Internal method to persist summaries with lock cleanup."""
        self._write_summaries(summaries)

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
            base_url=self.config.openai.openai_base_url,
            api_key=self.config.openai.openai_api_key,
        )
        self.markdown_file = markdown_file or Path(MARKDOWN_FILE)

    def _get_model_context_limit(self, model_name: str) -> int:
        """
        Get the context window limit for a model from the OpenAI API.

        Args:
            model_name: The model name

        Returns:
            The context window size in tokens
        """
        try:
            model_info = self.client.models.retrieve(model_name)
            # The context_window attribute contains the max input tokens
            if hasattr(model_info, "context_window"):
                return model_info.context_window
            # Fallback to a conservative default if not available
            return 8192
        except Exception:
            # If we can't retrieve model info, use a conservative default
            return 8192

    def _count_tokens(self, text: str, model: str) -> int:
        """
        Count the number of tokens in a text string.

        Args:
            text: The text to count tokens for
            model: The model name (used to get the correct tokenizer)

        Returns:
            The number of tokens
        """
        try:
            # Try to get the encoding for the specific model
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            # Fall back to cl100k_base encoding (used by gpt-4, gpt-3.5-turbo)
            encoding = tiktoken.get_encoding("cl100k_base")

        return len(encoding.encode(text))

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

        Raises:
            ContextWindowExceededError: If the prompt exceeds the model's context window
        """
        model = self.config.openai.openai_summary_model
        summaries_text = self._format_summaries_for_prompt(summaries)
        prompt = OVERALL_SUMMARY_PROMPT.format(summaries=summaries_text)

        # Check if the prompt exceeds the model's context window
        token_count = self._count_tokens(prompt, model)
        context_limit = self._get_model_context_limit(model)

        # Leave some buffer for the response (typically 2000-4000 tokens)
        usable_limit = int(context_limit * 0.75)

        if token_count > usable_limit:
            raise ContextWindowExceededError(
                f"The combined work item summaries ({token_count:,} tokens) exceed the "
                f"model's context window limit ({context_limit:,} tokens, usable: {usable_limit:,}).\n\n"
                f"To fix this, try reducing the date range when syncing work items to generate fewer summaries.\n"
                f"For example: `whatdidido sync --start-date 2025-01-01 --end-date 2025-03-31`"
            )

        response = self.client.chat.completions.create(
            model=model,
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
        console = Console()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task(
                "Generating final summary from all work items...", total=None
            )
            markdown_summary = self._generate_overall_summary(summaries)

        # Save to file
        self.markdown_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.markdown_file, "w") as f:
            f.write(markdown_summary)

        # Print to stdout with rich markdown rendering
        md = Markdown(markdown_summary)
        console.print(md)

        return markdown_summary
