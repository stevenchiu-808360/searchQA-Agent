"""
Base class for CLI commands.
"""

import argparse
import json
from abc import ABC, abstractmethod
from typing import Any
from urllib.parse import quote

from searchqa.client import ReadOnlyESClient

DEFAULT_INDEX = "product_alias"


class BaseCommand(ABC):
    """
    A CLI subcommand.

    Subclasses set `name` and `help`, declare arguments in `add_arguments`,
    and implement `run`.
    """

    name: str
    help: str
    needs_es: bool = True

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:  # noqa: B027
        """
        Declare command-specific arguments.

        Args:
            parser: Subparser for this command.
        """

    @abstractmethod
    def run(self, args: argparse.Namespace, client: ReadOnlyESClient | None) -> Any:
        """
        Execute the command.

        Args:
            args: Parsed CLI arguments.
            client: ES client, or None when `needs_es` is False.

        Returns:
            JSON-serializable result.
        """

    @staticmethod
    def add_index_argument(parser: argparse.ArgumentParser) -> None:
        """Add the common `--index` option."""
        parser.add_argument(
            "--index", default=DEFAULT_INDEX, help=f"Index or alias (default: {DEFAULT_INDEX})"
        )

    @staticmethod
    def parse_json(value: str | None, label: str) -> dict[str, Any]:
        """
        Parse a JSON object from a CLI argument.

        Args:
            value: JSON string, or None.
            label: Argument name for error messages.

        Returns:
            Parsed dict (empty if value is None).

        Raises:
            ValueError: If value is not a JSON object.
        """
        if value is None:
            return {}
        parsed = json.loads(value)
        if not isinstance(parsed, dict):
            raise ValueError(f"{label} must be a JSON object")
        return parsed

    @staticmethod
    def segment(value: str) -> str:
        """Percent-encode a single path segment (doc id, name)."""
        return quote(value, safe="")
