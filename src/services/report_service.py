"""Service for generating reports from work items."""

from persist import DataStore
from summarize import (
    ContextWindowExceededError,
    OverallSummarizer,
    WorkItemSummarizer,
    WorkItemSummary,
)


class ReportResult:
    """Result of report generation."""

    def __init__(
        self,
        success: bool,
        work_item_count: int = 0,
        provider_count: int = 0,
        summary: str | None = None,
        error: str | None = None,
    ):
        self.success = success
        self.work_item_count = work_item_count
        self.provider_count = provider_count
        self.summary = summary
        self.error = error


class ReportService:
    """Handles generating reports from work items."""

    def __init__(
        self,
        data_store: DataStore | None = None,
        work_item_summarizer: WorkItemSummarizer | None = None,
        overall_summarizer: OverallSummarizer | None = None,
    ):
        """Initialize the report service.

        Args:
            data_store: DataStore instance. If None, creates a new one.
            work_item_summarizer: WorkItemSummarizer instance. If None, creates a new one.
            overall_summarizer: OverallSummarizer instance. If None, creates a new one.
        """
        self.data_store = data_store or DataStore()
        self.work_item_summarizer = work_item_summarizer or WorkItemSummarizer()
        self.overall_summarizer = overall_summarizer or OverallSummarizer()

    def generate_report(self) -> ReportResult:
        """Generate a complete report from all work items.

        Returns:
            ReportResult with summary or error
        """
        try:
            # Get all work items from data store
            work_items_by_provider = self.data_store.get_all_data()

            if not work_items_by_provider:
                return ReportResult(
                    success=False,
                    error="No work items found. Please sync data first.",
                )

            # Flatten all work items into a single list
            all_work_items = []
            for _, items in work_items_by_provider.items():
                all_work_items.extend(items)

            # Generate summaries for each work item
            work_item_summaries = self.work_item_summarizer.summarize_work_items(
                all_work_items
            )

            # Generate overall summary
            overall_summary = self.overall_summarizer.generate_and_save_summary(
                work_item_summaries
            )

            return ReportResult(
                success=True,
                work_item_count=len(all_work_items),
                provider_count=len(work_items_by_provider),
                summary=overall_summary,
            )

        except ContextWindowExceededError as e:
            # Provide a clear error message for context window issues
            return ReportResult(success=False, error=str(e))
        except Exception as e:
            return ReportResult(success=False, error=str(e))

    def get_work_item_summaries(self) -> list[WorkItemSummary]:
        """Get existing work item summaries.

        Returns:
            List of WorkItemSummary objects
        """
        return self.work_item_summarizer.get_summaries()
