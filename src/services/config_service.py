"""Service for managing configuration display."""

from pathlib import Path


class ConfigService:
    """Handles configuration file display with sensitive data anonymization."""

    def __init__(self, config_file: Path):
        """Initialize the config service.

        Args:
            config_file: Path to the configuration file
        """
        self.config_file = config_file
        self.sensitive_keys = ["API_KEY", "TOKEN", "PASSWORD"]

    def file_exists(self) -> bool:
        """Check if config file exists.

        Returns:
            True if config file exists, False otherwise
        """
        return self.config_file.exists()

    def is_empty(self) -> bool:
        """Check if config file is empty.

        Returns:
            True if config file is empty or has no content
        """
        if not self.file_exists():
            return True

        with open(self.config_file, "r") as f:
            return len(f.readlines()) == 0

    def anonymize_value(self, value: str) -> str:
        """Anonymize a sensitive value.

        Args:
            value: The value to anonymize

        Returns:
            Anonymized value showing first 4 and last 4 characters
        """
        if not value:
            return ""

        if len(value) > 8:
            return f"{value[:4]}...{value[-4:]}"
        else:
            return "****"

    def is_sensitive_key(self, key: str) -> bool:
        """Check if a key contains sensitive data.

        Args:
            key: The configuration key to check

        Returns:
            True if key appears to contain sensitive data
        """
        return any(sensitive in key.upper() for sensitive in self.sensitive_keys)

    def get_config_lines(self) -> list[str]:
        """Read and process configuration file lines.

        Returns:
            List of configuration lines with sensitive values anonymized
        """
        if not self.file_exists():
            return []

        with open(self.config_file, "r") as f:
            raw_lines = f.readlines()

        processed_lines = []

        for line in raw_lines:
            line = line.strip()

            # Keep empty lines and comments as-is
            if not line or line.startswith("#"):
                processed_lines.append(line)
                continue

            # Process key=value lines
            if "=" in line:
                key, value = line.split("=", 1)

                if self.is_sensitive_key(key):
                    if value:
                        anonymized = self.anonymize_value(value)
                        processed_lines.append(f"{key}={anonymized}")
                    else:
                        processed_lines.append(f"{key}=")
                else:
                    processed_lines.append(line)
            else:
                processed_lines.append(line)

        return processed_lines
