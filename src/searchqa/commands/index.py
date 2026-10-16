"""
Index inspection commands: doc, mapping, settings.
"""

import argparse
from typing import Any

from searchqa.client import ReadOnlyESClient
from searchqa.commands.base import BaseCommand


class DocCommand(BaseCommand):
    """Fetch a single document by id."""

    name = "doc"
    help = "Get a document by id"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        self.add_index_argument(parser)
        parser.add_argument("doc_id", help="Document id (product id)")
        parser.add_argument("--fields", help="Comma-separated _source fields to include")

    def run(self, args: argparse.Namespace, client: ReadOnlyESClient | None) -> Any:
        params = {"_source_includes": args.fields} if args.fields else None
        return client.get(
            f"/{args.index}/_doc/{self.segment(args.doc_id)}", params=params, allow_not_found=True
        )


class MappingCommand(BaseCommand):
    """Fetch index mapping, optionally for one field."""

    name = "mapping"
    help = "Get index mapping (optionally filtered to one field)"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        self.add_index_argument(parser)
        parser.add_argument("--field", help="Only show this top-level field")

    def run(self, args: argparse.Namespace, client: ReadOnlyESClient | None) -> Any:
        params = {"filter_path": f"*.mappings.properties.{args.field}"} if args.field else None
        return client.get(f"/{args.index}/_mapping", params=params)


class SettingsCommand(BaseCommand):
    """Fetch index settings, optionally only the analysis section."""

    name = "settings"
    help = "Get index settings"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        self.add_index_argument(parser)
        parser.add_argument(
            "--analysis", action="store_true", help="Only show analyzers, tokenizers and filters"
        )

    def run(self, args: argparse.Namespace, client: ReadOnlyESClient | None) -> Any:
        params = {"filter_path": "*.settings.index.analysis"} if args.analysis else None
        return client.get(f"/{args.index}/_settings", params=params)
