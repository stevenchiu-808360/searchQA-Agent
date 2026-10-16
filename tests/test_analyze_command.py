"""
Tests for AnalyzeCommand empty-token diagnostics.
"""

import argparse
import json
from typing import Any

from searchqa.commands.analyze import AnalyzeCommand


class FakeClient:
    """Returns canned `_analyze` responses and records payloads."""

    def __init__(self, plain: dict[str, Any], explained: dict[str, Any] | None = None):
        self.plain = plain
        self.explained = explained
        self.payloads: list[dict[str, Any]] = []

    def get(self, path: str, payload: dict[str, Any] | None = None, **_: Any) -> Any:
        self.payloads.append(payload)
        return self.explained if payload.get("explain") else self.plain


def _args() -> argparse.Namespace:
    return argparse.Namespace(
        index="product_alias",
        text="買一送一",
        analyzer="custom_ik_query",
        field=None,
        explain=False,
    )


def test_non_empty_result_makes_no_extra_call(capsys):
    client = FakeClient({"tokens": [{"token": "a", "position": 0, "type": "ENGLISH"}]})

    result = AnalyzeCommand().run(_args(), client)

    assert result == [{"token": "a", "position": 0, "type": "ENGLISH"}]
    assert len(client.payloads) == 1
    assert capsys.readouterr().err == ""


def test_empty_result_warns_on_stderr_and_keeps_stdout_shape(capsys):
    explained = {
        "detail": {
            "custom_analyzer": True,
            "tokenizer": {"name": "ik_smart", "tokens": []},
            "tokenfilters": [{"name": "lowercase", "tokens": []}],
        }
    }
    client = FakeClient({"tokens": []}, explained)

    result = AnalyzeCommand().run(_args(), client)

    assert result == []
    warning = json.loads(capsys.readouterr().err)["warning"]
    assert "tokenizer ik_smart" in warning


def test_reason_names_the_filter_that_removed_tokens():
    detail = {
        "custom_analyzer": True,
        "tokenizer": {"name": "ik_smart", "tokens": [{"token": "x"}]},
        "tokenfilters": [
            {"name": "lowercase", "tokens": [{"token": "x"}]},
            {"name": "stopwords_ik", "tokens": []},
        ],
    }

    assert "token filter stopwords_ik" in AnalyzeCommand.empty_reason(detail)


def test_reason_for_builtin_analyzer():
    detail = {"custom_analyzer": False, "analyzer": {"name": "ik_smart", "tokens": []}}

    assert "analyzer ik_smart" in AnalyzeCommand.empty_reason(detail)
