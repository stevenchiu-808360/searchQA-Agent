"""
Safety tests for ReadOnlyESClient. These guard the GET-only invariants.
"""

import json

import httpx
import pytest

from searchqa.client import BlockedRequestError, ReadOnlyESClient
from searchqa.config import Environment, ESConfig


class RecordingTransport(httpx.BaseTransport):
    """Fake transport that records requests instead of hitting the network."""

    def __init__(self):
        self.requests: list[httpx.Request] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(200, json={"ok": True})


@pytest.fixture
def transport() -> RecordingTransport:
    return RecordingTransport()


@pytest.fixture
def client(transport: RecordingTransport) -> ReadOnlyESClient:
    config = ESConfig(env=Environment.STAGE, host="http://es.test:9200", username="u", password="p")
    return ReadOnlyESClient(config, transport=transport)


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/product_alias/_analyze",
        "/_analyze",
        "/_render/template",
        "/product_alias/_search/template",
        "/product_alias/_search",
        "/product_alias/_doc/DYAJJU-1900J84D6",
        "/product_alias/_mapping",
        "/product_alias/_settings",
        "/_alias",
        "/_scripts/search_product_fuzzy",
        "/_ltr/_model/model_v9",
        "/_ltr/_featureset/product_features",
        "/_cat/indices",
    ],
)
def test_allowlisted_paths_send_get_without_body(client, transport, path):
    client.get(path, payload={"text": "禮卷"} if "_analyze" in path else None)

    request = transport.requests[-1]
    assert request.method == "GET"
    assert request.content == b""


@pytest.mark.parametrize(
    "path",
    [
        "/product_alias/_refresh",
        "/_refresh",
        "/product_alias/_flush",
        "/product_alias/_reload_search_analyzers",
        "/product_alias/_update/1",
        "/product_alias/_delete_by_query",
        "/product_alias/_update_by_query",
        "/_bulk",
        "/_security/user",
        "/_cluster/settings",
        "/_ingest/pipeline/x",
        "/_search/scroll",
        "/_pit",
        "/_async_search",
        "/product_alias/_doc/../_refresh",
        "/product_alias/_analyze?x=1",
        "/_scripts",
    ],
)
def test_non_allowlisted_paths_are_blocked_before_sending(client, transport, path):
    with pytest.raises(BlockedRequestError):
        client.get(path)
    assert transport.requests == []


def test_payload_goes_into_source_param(client, transport):
    payload = {"analyzer": "ik_smart", "text": "禮卷"}
    client.get("/product_alias/_analyze", payload=payload)

    params = transport.requests[-1].url.params
    assert json.loads(params["source"]) == payload
    assert params["source_content_type"] == "application/json"


def test_disallowed_query_param_is_blocked(client, transport):
    with pytest.raises(BlockedRequestError):
        client.get("/product_alias/_search", params={"scroll": "1m"})
    assert transport.requests == []


def test_too_long_url_is_blocked(client, transport):
    with pytest.raises(BlockedRequestError):
        client.get("/product_alias/_search", payload={"query": {"match": {"x": "a" * 5000}}})
    assert transport.requests == []


def test_no_public_method_accepts_http_method():
    public = [name for name in dir(ReadOnlyESClient) if not name.startswith("_")]
    assert sorted(public) == ["close", "get"]


@pytest.mark.parametrize("method", ["POST", "PUT", "DELETE", "PATCH", "HEAD"])
def test_guard_hook_blocks_non_get(method):
    request = httpx.Request(method, "http://es.test:9200/_search")
    with pytest.raises(BlockedRequestError):
        ReadOnlyESClient._guard_request(request)


def test_guard_hook_blocks_get_with_body():
    request = httpx.Request("GET", "http://es.test:9200/_search", content=b"{}")
    with pytest.raises(BlockedRequestError):
        ReadOnlyESClient._guard_request(request)


def test_password_not_in_repr():
    config = ESConfig(env=Environment.STAGE, host="h", username="u", password="secret")
    assert "secret" not in repr(config)


def test_allow_not_found_returns_404_body():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"found": False})

    config = ESConfig(env=Environment.STAGE, host="http://es.test:9200", username="u", password="p")
    client = ReadOnlyESClient(config, transport=httpx.MockTransport(handler))
    assert client.get("/product_alias/_doc/X", allow_not_found=True) == {"found": False}
