"""Tests for the ReportService."""

from unittest.mock import Mock

from src.services.report_service import ReportService, ReportResult


class TestReportResult:
    """Tests for ReportResult class."""

    def test_report_result_success(self):
        """Test creating a successful ReportResult."""
        result = ReportResult(
            success=True,
            work_item_count=10,
            provider_count=2,
            summary="# Overall Summary\n\nGreat work!",
        )

        assert result.success is True
        assert result.work_item_count == 10
        assert result.provider_count == 2
        assert result.summary == "# Overall Summary\n\nGreat work!"
        assert result.error is None

    def test_report_result_failure(self):
        """Test creating a failed ReportResult."""
        result = ReportResult(success=False, error="No work items found")

        assert result.success is False
        assert result.work_item_count == 0
        assert result.provider_count == 0
        assert result.summary is None
        assert result.error == "No work items found"


class TestReportService:
    """Tests for ReportService class."""

    def test_init_default(self):
        """Test initialization with default dependencies."""
        service = ReportService()

        assert service.data_store is not None
        assert service.work_item_summarizer is not None
        assert service.overall_summarizer is not None

    def test_init_with_dependencies(self):
        """Test initialization with custom dependencies."""
        mock_store = Mock()
        mock_work_summarizer = Mock()
        mock_overall_summarizer = Mock()

        service = ReportService(
            data_store=mock_store,
            work_item_summarizer=mock_work_summarizer,
            overall_summarizer=mock_overall_summarizer,
        )

        assert service.data_store is mock_store
        assert service.work_item_summarizer is mock_work_summarizer
        assert service.overall_summarizer is mock_overall_summarizer

    def test_generate_report_success(self, sample_work_item):
        """Test generating a report successfully."""
        mock_store = Mock()
        mock_store.get_all_data.return_value = {
            "Jira": [sample_work_item],
            "Linear": [sample_work_item],
        }

        mock_summary = Mock()
        mock_summary.work_item_id = "TEST-123"

        mock_work_summarizer = Mock()
        mock_work_summarizer.summarize_work_items.return_value = [
            mock_summary,
            mock_summary,
        ]

        mock_overall_summarizer = Mock()
        mock_overall_summarizer.generate_and_save_summary.return_value = (
            "# Summary\n\nGreat work!"
        )

        service = ReportService(
            data_store=mock_store,
            work_item_summarizer=mock_work_summarizer,
            overall_summarizer=mock_overall_summarizer,
        )

        result = service.generate_report()

        assert result.success is True
        assert result.work_item_count == 2
        assert result.provider_count == 2
        assert result.summary == "# Summary\n\nGreat work!"
        assert result.error is None

        mock_store.get_all_data.assert_called_once()
        mock_work_summarizer.summarize_work_items.assert_called_once()
        mock_overall_summarizer.generate_and_save_summary.assert_called_once()

    def test_generate_report_no_work_items(self):
        """Test generating a report when no work items exist."""
        mock_store = Mock()
        mock_store.get_all_data.return_value = {}

        service = ReportService(data_store=mock_store)
        result = service.generate_report()

        assert result.success is False
        assert result.error == "No work items found. Please sync data first."
        assert result.work_item_count == 0
        assert result.provider_count == 0

    def test_generate_report_summarization_error(self, sample_work_item):
        """Test generating a report when summarization fails."""
        mock_store = Mock()
        mock_store.get_all_data.return_value = {"Jira": [sample_work_item]}

        mock_work_summarizer = Mock()
        mock_work_summarizer.summarize_work_items.side_effect = Exception(
            "OpenAI API error"
        )

        service = ReportService(
            data_store=mock_store, work_item_summarizer=mock_work_summarizer
        )

        result = service.generate_report()

        assert result.success is False
        assert result.error == "OpenAI API error"

    def test_generate_report_overall_summary_error(self, sample_work_item):
        """Test generating a report when overall summary fails."""
        mock_store = Mock()
        mock_store.get_all_data.return_value = {"Jira": [sample_work_item]}

        mock_summary = Mock()
        mock_work_summarizer = Mock()
        mock_work_summarizer.summarize_work_items.return_value = [mock_summary]

        mock_overall_summarizer = Mock()
        mock_overall_summarizer.generate_and_save_summary.side_effect = Exception(
            "File write error"
        )

        service = ReportService(
            data_store=mock_store,
            work_item_summarizer=mock_work_summarizer,
            overall_summarizer=mock_overall_summarizer,
        )

        result = service.generate_report()

        assert result.success is False
        assert result.error == "File write error"

    def test_generate_report_multiple_providers(
        self, sample_work_item, minimal_work_item
    ):
        """Test generating a report with multiple providers."""
        mock_store = Mock()
        mock_store.get_all_data.return_value = {
            "Jira": [sample_work_item, sample_work_item],
            "Linear": [minimal_work_item],
            "GitHub": [minimal_work_item, minimal_work_item],
        }

        mock_summary = Mock()
        mock_work_summarizer = Mock()
        mock_work_summarizer.summarize_work_items.return_value = [mock_summary] * 5

        mock_overall_summarizer = Mock()
        mock_overall_summarizer.generate_and_save_summary.return_value = "Summary"

        service = ReportService(
            data_store=mock_store,
            work_item_summarizer=mock_work_summarizer,
            overall_summarizer=mock_overall_summarizer,
        )

        result = service.generate_report()

        assert result.success is True
        assert result.work_item_count == 5  # 2 + 1 + 2
        assert result.provider_count == 3

    def test_get_work_item_summaries(self):
        """Test getting existing work item summaries."""
        mock_summary1 = Mock()
        mock_summary2 = Mock()

        mock_work_summarizer = Mock()
        mock_work_summarizer.get_summaries.return_value = [mock_summary1, mock_summary2]

        service = ReportService(work_item_summarizer=mock_work_summarizer)
        summaries = service.get_work_item_summaries()

        assert len(summaries) == 2
        assert summaries[0] is mock_summary1
        assert summaries[1] is mock_summary2

        mock_work_summarizer.get_summaries.assert_called_once()
