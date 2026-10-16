"""
Tests for SearchCommand payload building and output shaping.
"""

import argparse
from typing import Any

from searchqa.commands.template import SearchCommand


class FakeClient:
    """Records the last GET and returns a canned _search/template response."""

    def __init__(self, response: dict[str, Any]):
        self.response = response
        self.path: str | None = None
        self.payload: dict[str, Any] | None = None

    def get(self, path: str, payload: dict[str, Any] | None = None, **_: Any) -> Any:
        self.path = path
        self.payload = payload
        return self.response


def _args(**overrides: Any) -> argparse.Namespace:
    values = {
        "index": "product_alias",
        "template_id": "search_product_exact",
        "params": '{"query": "q"}',
        "fields": None,
        "explain": False,
        "raw": False,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def _response(with_explanation: bool) -> dict[str, Any]:
    hit: dict[str, Any] = {"_id": "A1", "_score": 1.5, "_source": {"IT_NAME": "x"}}
    if with_explanation:
        hit["_explanation"] = {"value": 1.5, "description": "sum", "details": []}
    return {"hits": {"total": {"value": 1, "relation": "eq"}, "hits": [hit]}}


def test_explain_is_top_level_not_in_params():
    client = FakeClient(_response(with_explanation=True))

    SearchCommand().run(_args(explain=True), client)

    assert client.payload["explain"] is True
    assert "explain" not in client.payload["params"]


def test_no_explain_by_default():
    client = FakeClient(_response(with_explanation=False))

    SearchCommand().run(_args(), client)

    assert "explain" not in client.payload
    assert client.payload["params"] == {"query": "q"}


def test_explanation_is_included_in_compact_output():
    client = FakeClient(_response(with_explanation=True))

    result = SearchCommand().run(_args(explain=True), client)

    assert result["hits"][0]["explanation"]["value"] == 1.5
