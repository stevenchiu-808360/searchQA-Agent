"""
Tokenization command.
"""

import argparse
import json
import sys
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
        tokens = [
            {"token": t["token"], "position": t["position"], "type": t["type"]}
            for t in response["tokens"]
        ]
        if not tokens:
            self._warn_empty(client, args.index, payload)
        return tokens

    def _warn_empty(self, client: ReadOnlyESClient, index: str, payload: dict[str, Any]) -> None:
        """
        Print a stderr warning naming the stage that removed every token.

        Args:
            client: ES client.
            index: Index used for the analysis.
            payload: The original `_analyze` payload (without `explain`).
        """
        detail = client.get(f"/{index}/_analyze", payload={**payload, "explain": True})["detail"]
        message = self.empty_reason(detail)
        print(json.dumps({"warning": message}, ensure_ascii=False), file=sys.stderr)

    @staticmethod
    def empty_reason(detail: dict[str, Any]) -> str:
        """
        Explain why an `_analyze` call produced no tokens.

        Args:
            detail: The `detail` object of an `_analyze` response with `explain: true`.

        Returns:
            A one-line description of the first stage whose output was empty.
        """
        if not detail.get("custom_analyzer"):
            name = detail.get("analyzer", {}).get("name", "analyzer")
            return f"No tokens: analyzer {name} produced no tokens."
        tokenizer = detail.get("tokenizer", {})
        if not tokenizer.get("tokens"):
            return (
                f"No tokens: tokenizer {tokenizer.get('name')} already produced no tokens "
                "(dictionary or stopword handling inside the tokenizer); no filter is involved."
            )
        for token_filter in detail.get("tokenfilters", []):
            if not token_filter.get("tokens"):
                return (
                    f"No tokens: all tokens were removed by token filter "
                    f"{token_filter.get('name')}."
                )
        return "No tokens: the analyzer produced no tokens."
