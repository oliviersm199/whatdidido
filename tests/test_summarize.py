"""
Tests for the summarization functionality.
"""

import json
import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from src.summarize import (
    ContextWindowExceededError,
    WorkItemSummary,
    WorkItemSummarizer,
    OverallSummarizer,
)


class TestWorkItemSummary:
    """Tests for the WorkItemSummary model."""

    def test_create_work_item_summary(self):
        """Test creating a WorkItemSummary."""
        summary = WorkItemSummary(
            work_item_id="TEST-123",
            title="Test work item",
            summary="This is a test summary of the work item.",
            provider="jira",
            created_at="2025-01-15T10:00:00Z",
            updated_at="2025-01-20T15:30:00Z",
            summarized_at="2025-01-21T12:00:00Z",
        )

        assert summary.work_item_id == "TEST-123"
        assert summary.title == "Test work item"
        assert summary.summary == "This is a test summary of the work item."
        assert summary.provider == "jira"
        assert summary.created_at == "2025-01-15T10:00:00Z"
        assert summary.updated_at == "2025-01-20T15:30:00Z"
        assert summary.summarized_at == "2025-01-21T12:00:00Z"

    def test_work_item_summary_serialization(self):
        """Test that WorkItemSummary can be serialized."""
        summary = WorkItemSummary(
            work_item_id="TEST-123",
            title="Test",
            summary="Summary",
            provider="jira",
            created_at="2025-01-15T10:00:00Z",
            updated_at="2025-01-20T15:30:00Z",
            summarized_at="2025-01-21T12:00:00Z",
        )

        data = summary.model_dump()
        assert isinstance(data, dict)
        assert data["work_item_id"] == "TEST-123"
        assert data["summary"] == "Summary"


class TestWorkItemSummarizer:
    """Tests for the WorkItemSummarizer class."""

    @patch("src.summarize.get_config")
    @patch("src.summarize.OpenAI")
    def test_init_creates_summary_file(self, mock_openai, mock_get_config, tmp_path):
        """Test that WorkItemSummarizer creates the summary file on initialization."""
        # Mock config
        mock_config = Mock()
        mock_config.openai.openai_base_url = "https://api.openai.com/v1"
        mock_config.openai.openai_api_key = "test-key"
        mock_get_config.return_value = mock_config

        summary_file = tmp_path / "summaries.json"
        WorkItemSummarizer(summary_file=summary_file)

        assert summary_file.exists()

        # Should create empty JSON array
        with open(summary_file, "r") as f:
            data = json.load(f)
            assert data == []

    @patch("src.summarize.get_config")
    @patch("src.summarize.OpenAI")
    def test_init_with_existing_file(self, mock_openai, mock_get_config, tmp_path):
        """Test that WorkItemSummarizer doesn't overwrite existing file."""
        mock_config = Mock()
        mock_config.openai.openai_base_url = "https://api.openai.com/v1"
        mock_config.openai.openai_api_key = "test-key"
        mock_get_config.return_value = mock_config

        summary_file = tmp_path / "existing.json"

        # Create file with existing data
        existing_data = [{"work_item_id": "EXIST-1", "summary": "test"}]
        with open(summary_file, "w") as f:
            json.dump(existing_data, f)

        WorkItemSummarizer(summary_file=summary_file)

        # Should not overwrite
        with open(summary_file, "r") as f:
            data = json.load(f)
            assert len(data) == 1

    @patch("src.summarize.get_config")
    @patch("src.summarize.OpenAI")
    def test_generate_summary(
        self, mock_openai_class, mock_get_config, tmp_path, sample_work_item
    ):
        """Test generating a summary for a single work item."""
        mock_config = Mock()
        mock_config.openai.openai_base_url = "https://api.openai.com/v1"
        mock_config.openai.openai_api_key = "test-key"
        mock_config.openai.openai_workitem_summary_model = "gpt-4"
        mock_get_config.return_value = mock_config

        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Generated summary for TEST-123"

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        summary_file = tmp_path / "summaries.json"
        summarizer = WorkItemSummarizer(summary_file=summary_file)

        # Generate summary
        summary_text = summarizer._generate_summary(sample_work_item)

        assert summary_text == "Generated summary for TEST-123"
        mock_client.chat.completions.create.assert_called_once()

        # Verify prompt was formatted correctly
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]["model"] == "gpt-4"
        messages = call_args[1]["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert "TEST-123" in messages[0]["content"]
        assert sample_work_item.title in messages[0]["content"]

    @patch("src.summarize.get_config")
    @patch("src.summarize.OpenAI")
    def test_summarize_work_items(
        self, mock_openai_class, mock_get_config, tmp_path, sample_work_item
    ):
        """Test summarizing a list of work items."""
        mock_config = Mock()
        mock_config.openai.openai_base_url = "https://api.openai.com/v1"
        mock_config.openai.openai_api_key = "test-key"
        mock_config.openai.openai_workitem_summary_model = "gpt-4"
        mock_get_config.return_value = mock_config

        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Generated summary"

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        summary_file = tmp_path / "summaries.json"
        summarizer = WorkItemSummarizer(summary_file=summary_file)

        # Summarize items
        summaries = summarizer.summarize_work_items([sample_work_item])

        assert len(summaries) == 1
        assert isinstance(summaries[0], WorkItemSummary)
        assert summaries[0].work_item_id == sample_work_item.id
        assert summaries[0].title == sample_work_item.title
        assert summaries[0].summary == "Generated summary"
        assert summaries[0].provider == sample_work_item.provider

        # Verify summaries were persisted
        with open(summary_file, "r") as f:
            data = json.load(f)
            assert len(data) == 1
            assert data[0]["work_item_id"] == sample_work_item.id

    @patch("src.summarize.get_config")
    @patch("src.summarize.OpenAI")
    def test_summarize_multiple_work_items(
        self,
        mock_openai_class,
        mock_get_config,
        tmp_path,
        sample_work_item,
        minimal_work_item,
    ):
        """Test summarizing multiple work items."""
        mock_config = Mock()
        mock_config.openai.openai_base_url = "https://api.openai.com/v1"
        mock_config.openai.openai_api_key = "test-key"
        mock_config.openai.openai_workitem_summary_model = "gpt-4"
        mock_get_config.return_value = mock_config

        # Mock OpenAI to return different summaries
        call_count = 0

        def create_response(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = f"Summary {call_count}"
            return mock_response

        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = create_response
        mock_openai_class.return_value = mock_client

        summary_file = tmp_path / "summaries.json"
        summarizer = WorkItemSummarizer(summary_file=summary_file)

        # Summarize multiple items
        summaries = summarizer.summarize_work_items(
            [sample_work_item, minimal_work_item]
        )

        assert len(summaries) == 2
        assert summaries[0].work_item_id == sample_work_item.id
        assert summaries[1].work_item_id == minimal_work_item.id
        assert summaries[0].summary == "Summary 1"
        assert summaries[1].summary == "Summary 2"

    @patch("src.summarize.get_config")
    @patch("src.summarize.OpenAI")
    def test_get_summaries(self, mock_openai_class, mock_get_config, tmp_path):
        """Test retrieving stored summaries."""
        mock_config = Mock()
        mock_config.openai.openai_base_url = "https://api.openai.com/v1"
        mock_config.openai.openai_api_key = "test-key"
        mock_get_config.return_value = mock_config

        summary_file = tmp_path / "summaries.json"

        # Pre-populate file with summaries
        summaries_data = [
            {
                "work_item_id": "TEST-1",
                "title": "Test 1",
                "summary": "Summary 1",
                "provider": "jira",
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
                "summarized_at": "2025-01-21T12:00:00Z",
            },
            {
                "work_item_id": "TEST-2",
                "title": "Test 2",
                "summary": "Summary 2",
                "provider": "linear",
                "created_at": "2025-01-02T00:00:00Z",
                "updated_at": "2025-01-02T00:00:00Z",
                "summarized_at": "2025-01-21T12:00:00Z",
            },
        ]

        summary_file.parent.mkdir(parents=True, exist_ok=True)
        with open(summary_file, "w") as f:
            json.dump(summaries_data, f)

        summarizer = WorkItemSummarizer(summary_file=summary_file)
        summaries = summarizer.get_summaries()

        assert len(summaries) == 2
        assert isinstance(summaries[0], WorkItemSummary)
        assert summaries[0].work_item_id == "TEST-1"
        assert summaries[1].work_item_id == "TEST-2"

    @patch("src.summarize.get_config")
    @patch("src.summarize.OpenAI")
    def test_summarized_at_timestamp(
        self, mock_openai_class, mock_get_config, tmp_path, sample_work_item
    ):
        """Test that summarized_at timestamp is set correctly."""
        mock_config = Mock()
        mock_config.openai.openai_base_url = "https://api.openai.com/v1"
        mock_config.openai.openai_api_key = "test-key"
        mock_config.openai.openai_workitem_summary_model = "gpt-4"
        mock_get_config.return_value = mock_config

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Summary"

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        summary_file = tmp_path / "summaries.json"
        summarizer = WorkItemSummarizer(summary_file=summary_file)

        before = datetime.now()
        summaries = summarizer.summarize_work_items([sample_work_item])
        after = datetime.now()

        # Parse the timestamp
        summarized_at = datetime.fromisoformat(summaries[0].summarized_at)

        # Should be between before and after
        assert before <= summarized_at <= after


class TestOverallSummarizer:
    """Tests for the OverallSummarizer class."""

    @patch("src.summarize.get_config")
    @patch("src.summarize.OpenAI")
    def test_format_summaries_for_prompt(
        self, mock_openai_class, mock_get_config, tmp_path
    ):
        """Test formatting summaries for the LLM prompt."""
        mock_config = Mock()
        mock_config.openai.openai_base_url = "https://api.openai.com/v1"
        mock_config.openai.openai_api_key = "test-key"
        mock_get_config.return_value = mock_config

        summarizer = OverallSummarizer(markdown_file=tmp_path / "output.md")

        summaries = [
            WorkItemSummary(
                work_item_id="TEST-1",
                title="First item",
                summary="Summary of first item",
                provider="jira",
                created_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z",
                summarized_at="2025-01-21T12:00:00Z",
            ),
            WorkItemSummary(
                work_item_id="TEST-2",
                title="Second item",
                summary="Summary of second item",
                provider="linear",
                created_at="2025-01-02T00:00:00Z",
                updated_at="2025-01-02T00:00:00Z",
                summarized_at="2025-01-21T12:00:00Z",
            ),
        ]

        formatted = summarizer._format_summaries_for_prompt(summaries)

        assert "TEST-1" in formatted
        assert "TEST-2" in formatted
        assert "First item" in formatted
        assert "Second item" in formatted
        assert "Summary of first item" in formatted
        assert "Summary of second item" in formatted
        assert "jira" in formatted
        assert "linear" in formatted

    @patch("src.summarize.get_config")
    @patch("src.summarize.OpenAI")
    def test_generate_overall_summary(
        self, mock_openai_class, mock_get_config, tmp_path
    ):
        """Test generating overall summary from work item summaries."""
        mock_config = Mock()
        mock_config.openai.openai_base_url = "https://api.openai.com/v1"
        mock_config.openai.openai_api_key = "test-key"
        mock_config.openai.openai_summary_model = "gpt-4"
        mock_get_config.return_value = mock_config

        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = (
            "# Overall Summary\n\nThis is the overall summary."
        )

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        # Mock the models.retrieve method to return context window
        mock_model_info = Mock()
        mock_model_info.context_window = 8192
        mock_client.models.retrieve.return_value = mock_model_info
        mock_openai_class.return_value = mock_client

        markdown_file = tmp_path / "output.md"
        summarizer = OverallSummarizer(markdown_file=markdown_file)

        summaries = [
            WorkItemSummary(
                work_item_id="TEST-1",
                title="Test",
                summary="Summary",
                provider="jira",
                created_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z",
                summarized_at="2025-01-21T12:00:00Z",
            )
        ]

        overall = summarizer._generate_overall_summary(summaries)

        assert overall == "# Overall Summary\n\nThis is the overall summary."
        mock_client.chat.completions.create.assert_called_once()

        # Verify model was correct
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]["model"] == "gpt-4"

    @patch("src.summarize.get_config")
    @patch("src.summarize.OpenAI")
    @patch("src.summarize.Progress")
    @patch("src.summarize.Console")
    def test_generate_and_save_summary(
        self,
        mock_console_class,
        mock_progress_class,
        mock_openai_class,
        mock_get_config,
        tmp_path,
    ):
        """Test generating and saving overall summary."""
        mock_config = Mock()
        mock_config.openai.openai_base_url = "https://api.openai.com/v1"
        mock_config.openai.openai_api_key = "test-key"
        mock_config.openai.openai_summary_model = "gpt-4"
        mock_get_config.return_value = mock_config

        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "# Summary\n\nContent here."

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        # Mock the models.retrieve method to return context window
        mock_model_info = Mock()
        mock_model_info.context_window = 8192
        mock_client.models.retrieve.return_value = mock_model_info
        mock_openai_class.return_value = mock_client

        # Mock console
        mock_console = Mock()
        mock_console_class.return_value = mock_console

        # Mock progress
        mock_progress = Mock()
        mock_progress.__enter__ = Mock(return_value=mock_progress)
        mock_progress.__exit__ = Mock(return_value=False)
        mock_progress_class.return_value = mock_progress

        markdown_file = tmp_path / "output.md"
        summarizer = OverallSummarizer(markdown_file=markdown_file)

        summaries = [
            WorkItemSummary(
                work_item_id="TEST-1",
                title="Test",
                summary="Summary",
                provider="jira",
                created_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z",
                summarized_at="2025-01-21T12:00:00Z",
            )
        ]

        result = summarizer.generate_and_save_summary(summaries)

        assert result == "# Summary\n\nContent here."

        # Verify file was saved
        assert markdown_file.exists()
        with open(markdown_file, "r") as f:
            content = f.read()
            assert content == "# Summary\n\nContent here."

        # Verify console was used
        mock_console.print.assert_called_once()

        # Verify progress was shown
        mock_progress.add_task.assert_called_once_with(
            "Generating final summary from all work items...", total=None
        )

    @patch("src.summarize.get_config")
    @patch("src.summarize.OpenAI")
    def test_markdown_file_nested_directory(
        self, mock_openai_class, mock_get_config, tmp_path
    ):
        """Test that markdown file creates nested directories if needed."""
        mock_config = Mock()
        mock_config.openai.openai_base_url = "https://api.openai.com/v1"
        mock_config.openai.openai_api_key = "test-key"
        mock_config.openai.openai_summary_model = "gpt-4"
        mock_get_config.return_value = mock_config

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Content"

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        # Mock the models.retrieve method to return context window
        mock_model_info = Mock()
        mock_model_info.context_window = 8192
        mock_client.models.retrieve.return_value = mock_model_info
        mock_openai_class.return_value = mock_client

        markdown_file = tmp_path / "nested" / "dir" / "output.md"

        with (
            patch("src.summarize.Console"),
            patch("src.summarize.Progress") as mock_progress_class,
        ):
            # Mock progress
            mock_progress = Mock()
            mock_progress.__enter__ = Mock(return_value=mock_progress)
            mock_progress.__exit__ = Mock(return_value=False)
            mock_progress_class.return_value = mock_progress

            summarizer = OverallSummarizer(markdown_file=markdown_file)

            summaries = [
                WorkItemSummary(
                    work_item_id="TEST-1",
                    title="Test",
                    summary="Summary",
                    provider="jira",
                    created_at="2025-01-01T00:00:00Z",
                    updated_at="2025-01-01T00:00:00Z",
                    summarized_at="2025-01-21T12:00:00Z",
                )
            ]

            summarizer.generate_and_save_summary(summaries)

            assert markdown_file.exists()
            assert markdown_file.parent.exists()

    @patch("src.summarize.get_config")
    @patch("src.summarize.OpenAI")
    def test_context_window_exceeded_error(
        self, mock_openai_class, mock_get_config, tmp_path
    ):
        """Test that ContextWindowExceededError is raised when prompt is too large."""
        mock_config = Mock()
        mock_config.openai.openai_base_url = "https://api.openai.com/v1"
        mock_config.openai.openai_api_key = "test-key"
        mock_config.openai.openai_summary_model = "gpt-4"
        mock_get_config.return_value = mock_config

        mock_client = Mock()
        # Mock a small context window
        mock_model_info = Mock()
        mock_model_info.context_window = 100  # Very small limit
        mock_client.models.retrieve.return_value = mock_model_info
        mock_openai_class.return_value = mock_client

        markdown_file = tmp_path / "output.md"
        summarizer = OverallSummarizer(markdown_file=markdown_file)

        # Create many summaries to exceed the limit
        summaries = [
            WorkItemSummary(
                work_item_id=f"TEST-{i}",
                title=f"Test item {i} with a very long title to increase token count",
                summary=f"This is a very detailed summary for item {i} with lots of words to make it long",
                provider="jira",
                created_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z",
                summarized_at="2025-01-21T12:00:00Z",
            )
            for i in range(50)  # Many items to exceed the limit
        ]

        # Should raise ContextWindowExceededError
        with pytest.raises(ContextWindowExceededError) as exc_info:
            summarizer._generate_overall_summary(summaries)

        # Verify error message contains helpful information
        error_message = str(exc_info.value)
        assert "context window limit" in error_message
        assert "reducing the date range" in error_message
