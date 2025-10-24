"""
Tests for lock utilities (with_lock_cleanup decorator).
"""

import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.utils.lock_utils import with_lock_cleanup


class TestWithLockCleanup:
    """Tests for the with_lock_cleanup decorator."""

    def test_decorator_creates_and_removes_lock_file(self, tmp_path):
        """Test that decorator creates lock file and removes it after execution."""
        lock_file = tmp_path / "test.lock"

        @with_lock_cleanup(lock_file)
        def dummy_function():
            # Lock file should exist during execution
            assert lock_file.exists()
            return "success"

        # Lock file should not exist before
        assert not lock_file.exists()

        result = dummy_function()

        # Function should execute successfully
        assert result == "success"

        # Lock file should be cleaned up after
        assert not lock_file.exists()

    def test_decorator_with_string_path(self, tmp_path):
        """Test that decorator works with string path."""
        lock_file = str(tmp_path / "test_string.lock")

        @with_lock_cleanup(lock_file)
        def dummy_function():
            return "success"

        result = dummy_function()
        assert result == "success"
        assert not os.path.exists(lock_file)

    def test_decorator_with_path_object(self, tmp_path):
        """Test that decorator works with Path object."""
        lock_file = Path(tmp_path / "test_path.lock")

        @with_lock_cleanup(lock_file)
        def dummy_function():
            return "success"

        result = dummy_function()
        assert result == "success"
        assert not lock_file.exists()

    def test_decorator_with_method(self, tmp_path):
        """Test that decorator works with class methods."""
        lock_file = tmp_path / "method.lock"

        class TestClass:
            @with_lock_cleanup(lock_file)
            def test_method(self, value):
                return value * 2

        obj = TestClass()
        result = obj.test_method(5)
        assert result == 10
        assert not lock_file.exists()

    def test_decorator_cleanup_on_exception(self, tmp_path):
        """Test that lock file is cleaned up even when function raises exception."""
        lock_file = tmp_path / "exception.lock"

        @with_lock_cleanup(lock_file)
        def failing_function():
            raise ValueError("Test exception")

        with pytest.raises(ValueError, match="Test exception"):
            failing_function()

        # Lock file should still be cleaned up
        assert not lock_file.exists()

    def test_decorator_cleanup_on_return_early(self, tmp_path):
        """Test that lock file is cleaned up with early return."""
        lock_file = tmp_path / "early_return.lock"

        @with_lock_cleanup(lock_file)
        def early_return_function(condition):
            if condition:
                return "early"
            return "normal"

        result = early_return_function(True)
        assert result == "early"
        assert not lock_file.exists()

    def test_decorator_with_arguments_and_kwargs(self, tmp_path):
        """Test that decorator preserves function arguments."""
        lock_file = tmp_path / "args.lock"

        @with_lock_cleanup(lock_file)
        def function_with_args(a, b, c=None):
            return {"a": a, "b": b, "c": c}

        result = function_with_args(1, 2, c=3)
        assert result == {"a": 1, "b": 2, "c": 3}
        assert not lock_file.exists()

    def test_decorator_preserves_function_metadata(self, tmp_path):
        """Test that decorator preserves function name and docstring."""
        lock_file = tmp_path / "metadata.lock"

        @with_lock_cleanup(lock_file)
        def documented_function():
            """This is a documented function."""
            return True

        assert documented_function.__name__ == "documented_function"
        assert documented_function.__doc__ == "This is a documented function."

    def test_multiple_decorated_functions_different_locks(self, tmp_path):
        """Test multiple functions with different lock files."""
        lock_file1 = tmp_path / "lock1.lock"
        lock_file2 = tmp_path / "lock2.lock"

        @with_lock_cleanup(lock_file1)
        def function1():
            return "func1"

        @with_lock_cleanup(lock_file2)
        def function2():
            return "func2"

        result1 = function1()
        result2 = function2()

        assert result1 == "func1"
        assert result2 == "func2"
        assert not lock_file1.exists()
        assert not lock_file2.exists()

    def test_decorator_handles_nonexistent_lock_on_cleanup(self, tmp_path):
        """Test that decorator handles case where lock file doesn't exist during cleanup."""
        lock_file = tmp_path / "nonexistent.lock"

        @with_lock_cleanup(lock_file)
        def function_that_removes_lock():
            # Simulate lock file being removed by another process
            if lock_file.exists():
                os.remove(str(lock_file))
            return "success"

        # Should not raise exception even if lock is already gone
        result = function_that_removes_lock()
        assert result == "success"

    def test_decorator_handles_permission_error_on_cleanup(self, tmp_path):
        """Test that decorator handles permission errors during cleanup gracefully."""
        lock_file = tmp_path / "permission.lock"

        @with_lock_cleanup(lock_file)
        def dummy_function():
            return "success"

        # Mock os.remove to raise PermissionError
        with patch("os.remove") as mock_remove:
            mock_remove.side_effect = PermissionError("Cannot remove lock")

            # Should not raise exception, just ignore the error
            result = dummy_function()
            assert result == "success"

    def test_decorator_reentrant_calls(self, tmp_path):
        """Test that decorator can be called multiple times sequentially."""
        lock_file = tmp_path / "reentrant.lock"
        call_count = 0

        @with_lock_cleanup(lock_file)
        def counting_function():
            nonlocal call_count
            call_count += 1
            return call_count

        # Call multiple times
        result1 = counting_function()
        result2 = counting_function()
        result3 = counting_function()

        assert result1 == 1
        assert result2 == 2
        assert result3 == 3
        assert not lock_file.exists()

    def test_decorator_with_nested_directory_path(self, tmp_path):
        """Test decorator with lock file in nested directory structure."""
        nested_dir = tmp_path / "subdir" / "nested"
        nested_dir.mkdir(parents=True)
        lock_file = nested_dir / "nested.lock"

        @with_lock_cleanup(lock_file)
        def dummy_function():
            return "success"

        result = dummy_function()
        assert result == "success"
        assert not lock_file.exists()

    def test_decorator_with_return_value_types(self, tmp_path):
        """Test that decorator preserves various return value types."""
        lock_file = tmp_path / "return_types.lock"

        @with_lock_cleanup(lock_file)
        def return_none():
            return None

        @with_lock_cleanup(lock_file)
        def return_dict():
            return {"key": "value"}

        @with_lock_cleanup(lock_file)
        def return_list():
            return [1, 2, 3]

        assert return_none() is None
        assert return_dict() == {"key": "value"}
        assert return_list() == [1, 2, 3]
        assert not lock_file.exists()

    @patch("src.utils.lock_utils.FileLock")
    def test_decorator_uses_filelock_correctly(self, mock_filelock_class, tmp_path):
        """Test that decorator uses FileLock with correct parameters."""
        lock_file = tmp_path / "mock_test.lock"
        mock_lock = Mock()
        mock_lock.__enter__ = Mock(return_value=mock_lock)
        mock_lock.__exit__ = Mock(return_value=None)
        mock_filelock_class.return_value = mock_lock

        @with_lock_cleanup(lock_file)
        def dummy_function():
            return "success"

        result = dummy_function()

        # Verify FileLock was created with correct path and timeout
        mock_filelock_class.assert_called_once_with(str(lock_file), timeout=10)

        # Verify lock context manager was used
        mock_lock.__enter__.assert_called_once()
        mock_lock.__exit__.assert_called_once()

        assert result == "success"

    def test_decorator_lock_exclusivity(self, tmp_path):
        """Test that decorated function properly locks access."""
        lock_file = tmp_path / "exclusive.lock"
        execution_order = []

        @with_lock_cleanup(lock_file)
        def locked_function(name):
            execution_order.append(f"{name}_start")
            execution_order.append(f"{name}_end")
            return name

        # This test just verifies the function can execute
        # Testing actual concurrent locking would require threading
        result = locked_function("test")
        assert result == "test"
        assert execution_order == ["test_start", "test_end"]
        assert not lock_file.exists()
