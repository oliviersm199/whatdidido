"""Service for cleaning up whatdidido data files."""

from pathlib import Path


class CleanResult:
    """Result of a clean operation."""

    def __init__(self, deleted_files: list[Path], errors: dict[Path, str]):
        """Initialize clean result.

        Args:
            deleted_files: List of successfully deleted files
            errors: Dictionary mapping files to error messages
        """
        self.deleted_files = deleted_files
        self.errors = errors
        self.success = len(errors) == 0


class CleanService:
    """Handles cleaning up whatdidido data files."""

    DEFAULT_FILES = [
        "whatdidido.json",
        "whatdidido-summary.json",
        "whatdidido.json.lock",
        "whatdidido-summary.json.lock",
        "whatdidido.md",
    ]

    def __init__(self, base_dir: Path | None = None):
        """Initialize the clean service.

        Args:
            base_dir: Base directory for files. If None, uses current directory.
        """
        self.base_dir = base_dir or Path(".")

    def get_files_to_clean(self) -> list[Path]:
        """Get list of whatdidido files that exist and can be cleaned.

        Returns:
            List of existing whatdidido files
        """
        files_to_clean = []

        for filename in self.DEFAULT_FILES:
            file_path = self.base_dir / filename
            if file_path.exists():
                files_to_clean.append(file_path)

        return files_to_clean

    def clean(self) -> CleanResult:
        """Delete all whatdidido files.

        Returns:
            CleanResult with lists of deleted files and errors
        """
        files_to_delete = self.get_files_to_clean()
        deleted_files = []
        errors = {}

        for file_path in files_to_delete:
            try:
                file_path.unlink()
                deleted_files.append(file_path)
            except Exception as e:
                errors[file_path] = str(e)

        return CleanResult(deleted_files=deleted_files, errors=errors)
