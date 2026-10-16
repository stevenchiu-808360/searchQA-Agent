"""
Tokenization command.
"""

import argparse
from typing import Any

from searchqa.client import ReadOnlyESClient
from searchqa.commands.base import BaseCommand


class AnalyzeCommand(BaseCommand):
    """Run `_analyze` with an analyzer or a field's analyzer."""

    name = "analyze"
    help = "Tokenize text with an index analyzer or field analyzer"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        self.add_index_argument(parser)
        parser.add_argument("text", help="Text to analyze")
        target = parser.add_mutually_exclusive_group(required=True)
        target.add_argument("--analyzer", help="Analyzer name, e.g. custom_ik_syn_query")
        target.add_argument("--field", help="Use the search analyzer of this field")
        parser.add_argument(
            "--explain",
            action="store_true",
            help="Show output of the tokenizer and each token filter",
        )

    def run(self, args: argparse.Namespace, client: ReadOnlyESClient | None) -> Any:
        payload: dict[str, Any] = {"text": args.text}
        if args.analyzer:
            payload["analyzer"] = args.analyzer
        else:
            payload["field"] = args.field
        if args.explain:
            payload["explain"] = True
            return client.get(f"/{args.index}/_analyze", payload=payload)

        response = client.get(f"/{args.index}/_analyze", payload=payload)
        return [
            {"token": t["token"], "position": t["position"], "type": t["type"]}
            for t in response["tokens"]
        ]
