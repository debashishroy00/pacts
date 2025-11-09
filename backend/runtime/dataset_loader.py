"""
PACTS v3.1s - Dataset Loader

Load test data from CSV, JSONL, or YAML files for data-driven execution.

Supported formats:
- CSV: Comma-separated values with header row
- JSONL: JSON Lines (one JSON object per line)
- YAML: YAML array of objects

Example CSV:
    username,password,assert_after
    user1@example.com,secret1,Signed in
    user2@example.com,secret2,Verify your email

Example JSONL:
    {"username": "user1@example.com", "password": "secret1", "assert_after": "Signed in"}
    {"username": "user2@example.com", "password": "secret2", "assert_after": "Verify your email"}

Example YAML:
    - username: user1@example.com
      password: secret1
      assert_after: Signed in
    - username: user2@example.com
      password: secret2
      assert_after: Verify your email
"""

from __future__ import annotations
from typing import Iterator, Dict, Any, Optional
from pathlib import Path
import csv
import json
import yaml
import logging

logger = logging.getLogger(__name__)


class DatasetLoader:
    """Load test datasets from various file formats."""

    def __init__(self, file_path: str, format: Optional[str] = None):
        """
        Initialize dataset loader.

        Args:
            file_path: Path to dataset file
            format: File format (csv, jsonl, yaml) - auto-detected if None
        """
        self.file_path = Path(file_path)
        self.format = format or self._detect_format()

        if not self.file_path.exists():
            raise FileNotFoundError(f"Dataset file not found: {file_path}")

        logger.info(f"[Dataset] Loading {self.format.upper()} from {file_path}")

    def _detect_format(self) -> str:
        """
        Auto-detect file format from extension.

        Returns:
            Format string (csv, jsonl, yaml)

        Raises:
            ValueError: If format cannot be detected
        """
        suffix = self.file_path.suffix.lower()

        if suffix == ".csv":
            return "csv"
        elif suffix == ".jsonl":
            return "jsonl"
        elif suffix in [".yaml", ".yml"]:
            return "yaml"
        else:
            raise ValueError(f"Cannot auto-detect format for: {suffix}")

    def load(self, max_rows: Optional[int] = None, row_filter: Optional[Dict[str, Any]] = None) -> Iterator[Dict[str, Any]]:
        """
        Load dataset and yield rows as dictionaries.

        Args:
            max_rows: Maximum number of rows to load (None = all)
            row_filter: Filter rows by field values (e.g., {"id": "test1"})

        Yields:
            Dictionary for each row with row_id injected

        Example:
            for row in loader.load(max_rows=10):
                print(row)  # {"username": "...", "password": "...", "row_id": 0}
        """
        if self.format == "csv":
            yield from self._load_csv(max_rows, row_filter)
        elif self.format == "jsonl":
            yield from self._load_jsonl(max_rows, row_filter)
        elif self.format == "yaml":
            yield from self._load_yaml(max_rows, row_filter)
        else:
            raise ValueError(f"Unsupported format: {self.format}")

    def _load_csv(self, max_rows: Optional[int], row_filter: Optional[Dict[str, Any]]) -> Iterator[Dict[str, Any]]:
        """Load CSV file."""
        with open(self.file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            row_id = 0

            for row_dict in reader:
                # Apply filter if provided
                if row_filter and not self._matches_filter(row_dict, row_filter):
                    continue

                # Inject row_id
                row_dict['row_id'] = row_id
                yield row_dict

                row_id += 1
                if max_rows and row_id >= max_rows:
                    break

        logger.info(f"[Dataset] Loaded {row_id} rows from CSV")

    def _load_jsonl(self, max_rows: Optional[int], row_filter: Optional[Dict[str, Any]]) -> Iterator[Dict[str, Any]]:
        """Load JSONL file."""
        with open(self.file_path, 'r', encoding='utf-8') as f:
            row_id = 0

            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    row_dict = json.loads(line)
                except json.JSONDecodeError as e:
                    logger.warning(f"[Dataset] Skipping invalid JSON line {row_id}: {e}")
                    continue

                # Apply filter if provided
                if row_filter and not self._matches_filter(row_dict, row_filter):
                    continue

                # Inject row_id
                row_dict['row_id'] = row_id
                yield row_dict

                row_id += 1
                if max_rows and row_id >= max_rows:
                    break

        logger.info(f"[Dataset] Loaded {row_id} rows from JSONL")

    def _load_yaml(self, max_rows: Optional[int], row_filter: Optional[Dict[str, Any]]) -> Iterator[Dict[str, Any]]:
        """Load YAML file."""
        with open(self.file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        if not isinstance(data, list):
            raise ValueError("YAML dataset must be a list of objects")

        row_id = 0
        for row_dict in data:
            if not isinstance(row_dict, dict):
                logger.warning(f"[Dataset] Skipping non-dict row {row_id}")
                continue

            # Apply filter if provided
            if row_filter and not self._matches_filter(row_dict, row_filter):
                continue

            # Inject row_id
            row_dict['row_id'] = row_id
            yield row_dict

            row_id += 1
            if max_rows and row_id >= max_rows:
                break

        logger.info(f"[Dataset] Loaded {row_id} rows from YAML")

    def _matches_filter(self, row: Dict[str, Any], filter_dict: Dict[str, Any]) -> bool:
        """
        Check if row matches filter criteria.

        Args:
            row: Row dictionary
            filter_dict: Filter criteria (key=value pairs)

        Returns:
            True if row matches all filter criteria
        """
        for key, value in filter_dict.items():
            if key not in row or row[key] != value:
                return False
        return True

    def count(self) -> int:
        """
        Count total rows in dataset (without loading all into memory).

        Returns:
            Number of rows
        """
        if self.format == "csv":
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return sum(1 for _ in csv.DictReader(f))
        elif self.format == "jsonl":
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return sum(1 for line in f if line.strip())
        elif self.format == "yaml":
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                return len(data) if isinstance(data, list) else 0
        else:
            return 0


# Convenience functions
def load_dataset(file_path: str, **kwargs) -> Iterator[Dict[str, Any]]:
    """
    Quick load function without creating loader instance.

    Args:
        file_path: Path to dataset file
        **kwargs: Additional arguments for DatasetLoader.load()

    Yields:
        Dictionary for each row
    """
    loader = DatasetLoader(file_path)
    yield from loader.load(**kwargs)


def parse_row_filter(filter_str: str) -> Dict[str, Any]:
    """
    Parse CLI filter string to dictionary.

    Args:
        filter_str: Filter string in format "key=value,key2=value2"

    Returns:
        Filter dictionary

    Example:
        parse_row_filter("id=test1,env=prod") -> {"id": "test1", "env": "prod"}
    """
    if not filter_str:
        return {}

    filter_dict = {}
    for pair in filter_str.split(","):
        if "=" in pair:
            key, value = pair.split("=", 1)
            filter_dict[key.strip()] = value.strip()

    return filter_dict
