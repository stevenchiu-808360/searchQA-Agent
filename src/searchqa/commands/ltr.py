"""
Learning-to-rank inspection command.
"""

import argparse
from typing import Any

from searchqa.client import ReadOnlyESClient
from searchqa.commands.base import BaseCommand


class LtrCommand(BaseCommand):
    """Fetch an LTR model or feature set from the default feature store."""

    name = "ltr"
    help = "Get an LTR model or feature set"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        target = parser.add_mutually_exclusive_group(required=True)
        target.add_argument("--model", help="Model name, e.g. model_v9")
        target.add_argument("--featureset", help="Feature set name")

    def run(self, args: argparse.Namespace, client: ReadOnlyESClient | None) -> Any:
        if args.model:
            return client.get(f"/_ltr/_model/{self.segment(args.model)}")
        return client.get(f"/_ltr/_featureset/{self.segment(args.featureset)}")
