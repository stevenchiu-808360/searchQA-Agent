"""
Search template commands: render, search, script.
"""
import argparse
from typing import Any

from searchqa.client import ReadOnlyESClient
from searchqa.commands.base import BaseCommand


class RenderCommand(BaseCommand):
    """Render a stored search template into the actual query."""
    name = "render"
    help = "Render a stored search template with params"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("template_id", help="Stored template id, e.g. search_product_fuzzy")
        parser.add_argument("--params", help="Template params as a JSON object")

    def run(self, args: argparse.Namespace, client: ReadOnlyESClient | None) -> Any:
        params = self.parse_json(args.params, "--params")
        path = f"/_render/template/{self.segment(args.template_id)}"
        return client.get(path, payload={"params": params})


class SearchCommand(BaseCommand):
    """Run a stored search template and return compact hits."""
    name = "search"
    help = "Run a stored search template and list hits"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        self.add_index_argument(parser)
        parser.add_argument("template_id", help="Stored template id, e.g. search_product_fuzzy")
        parser.add_argument("--params", help="Template params as a JSON object")
        parser.add_argument("--fields", help="Comma-separated _source fields to include per hit")
        parser.add_argument("--explain", action="store_true",
                            help="Set template param explain=true and include score explanations")
        parser.add_argument("--raw", action="store_true", help="Return the full ES response")

    def run(self, args: argparse.Namespace, client: ReadOnlyESClient | None) -> Any:
        params = self.parse_json(args.params, "--params")
        if args.explain:
            params["explain"] = True
        response = client.get(f"/{args.index}/_search/template",
                              payload={"id": args.template_id, "params": params})
        if args.raw:
            return response

        fields = [f for f in (args.fields or "").split(",") if f]
        hits = []
        for rank, hit in enumerate(response["hits"]["hits"], start=1):
            item: dict[str, Any] = {"rank": rank, "id": hit["_id"], "score": hit.get("_score")}
            if fields:
                source = hit.get("_source", {})
                item["source"] = {f: source.get(f) for f in fields}
            if "matched_queries" in hit:
                item["matched_queries"] = hit["matched_queries"]
            if args.explain and "_explanation" in hit:
                item["explanation"] = hit["_explanation"]
            hits.append(item)
        return {"total": response["hits"]["total"], "hits": hits}


class ScriptCommand(BaseCommand):
    """Fetch a stored script/template as deployed on the cluster."""
    name = "script"
    help = "Get a stored search template from the cluster"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("template_id", help="Stored template id")

    def run(self, args: argparse.Namespace, client: ReadOnlyESClient | None) -> Any:
        return client.get(f"/_scripts/{self.segment(args.template_id)}")
