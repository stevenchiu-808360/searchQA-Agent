"""
GET-only Elasticsearch client.

Safety invariants (covered by tests/test_client.py):
1. The only HTTP method ever sent is GET; there is no public API that takes a method.
2. Requests never carry a body; payloads go in `?source=` with `source_content_type`.
3. Paths must match ENDPOINT_ALLOWLIST before any network call. Some ES GET endpoints
   have side effects (e.g. `_refresh`, `_flush`, `_reload_search_analyzers`), so
   "GET-only" alone is not sufficient.
4. A request hook re-checks method and body right before sending, as a last line of defense.
"""
import json
import re
from typing import Any

import httpx

from searchqa.config import ESConfig

# Index name / pattern: must not start with "_" so system endpoints never match.
_INDEX = r"[A-Za-z0-9*][A-Za-z0-9.*,_-]*"
# Single path segment for ids/names (doc ids are percent-encoded by callers).
_NAME = r"[A-Za-z0-9%][A-Za-z0-9%._-]*"

ENDPOINT_ALLOWLIST: tuple[re.Pattern[str], ...] = tuple(
    re.compile(rf"^/{pattern}$")
    for pattern in (
        r"",                                            # cluster info
        rf"(?:{_INDEX}/)?_analyze",
        rf"_render/template(?:/{_NAME})?",
        rf"{_INDEX}/_search(?:/template)?",
        rf"{_INDEX}/_doc/{_NAME}",
        rf"{_INDEX}/_mapping",
        rf"{_INDEX}/_settings",
        rf"(?:{_INDEX}/)?_alias(?:/{_NAME})?",
        rf"_scripts/{_NAME}",
        rf"_ltr(?:/{_NAME})?/_(?:featureset|feature|model)(?:/{_NAME})?",
        r"_cat/(?:indices|aliases)",
    )
)

QUERY_PARAM_ALLOWLIST = frozenset({
    "filter_path", "format", "h", "v", "s", "human", "typed_keys", "flat_settings",
    "include_defaults", "_source", "_source_includes", "_source_excludes",
    "stored_fields", "routing", "preference",
})

# ES default http.max_initial_line_length is 4kb; leave room for "GET " and " HTTP/1.1".
MAX_REQUEST_LINE = 4000


class ESClientError(Exception):
    """Raised for blocked requests or ES error responses."""


class BlockedRequestError(ESClientError):
    """Raised when a request violates a safety invariant. Nothing is sent."""


class ReadOnlyESClient:
    """
    Read-only Elasticsearch client that can only issue allowlisted GET requests.
    """

    def __init__(self, config: ESConfig, timeout: float = 30.0,
                 transport: httpx.BaseTransport | None = None):
        """
        Args:
            config: Connection settings for the target environment.
            timeout: Request timeout in seconds.
            transport: Optional httpx transport (used by tests).
        """
        self.config = config
        self._http = httpx.Client(
            base_url=config.host,
            auth=(config.username, config.password),
            timeout=timeout,
            follow_redirects=False,
            transport=transport,
            event_hooks={"request": [self._guard_request]},
        )

    def get(self, path: str, payload: dict[str, Any] | None = None,
            params: dict[str, str] | None = None, allow_not_found: bool = False) -> Any:
        """
        Send a GET request.

        Args:
            path: ES path starting with "/", e.g. "/product_alias/_analyze".
            payload: Request JSON, sent as the `source` query parameter.
            params: Extra query parameters (must be in QUERY_PARAM_ALLOWLIST).
            allow_not_found: Return the 404 body instead of raising (e.g. `found: false`).

        Returns:
            Parsed JSON response (or text for `_cat` endpoints without format=json).

        Raises:
            BlockedRequestError: If the path or params are not allowed, or the URL is too long.
            ESClientError: If ES returns an error status or is unreachable.
        """
        self._check_path(path)
        query = self._build_query(payload, params)
        request = self._http.build_request("GET", path, params=query)
        request_line = len(request.url.raw_path)
        if request_line > MAX_REQUEST_LINE:
            raise BlockedRequestError(
                f"Request URL is {request_line} bytes, over ES limit (~{MAX_REQUEST_LINE}). "
                "Use a search template id with params instead of an inline query."
            )

        try:
            response = self._http.send(request)
        except httpx.HTTPError as e:
            raise ESClientError(f"Request to {self.config.env.value} failed: {e}") from e

        if response.status_code == 404 and allow_not_found:
            return response.json()
        if response.status_code >= 400:
            raise ESClientError(f"ES {response.status_code} on GET {path}: {response.text[:2000]}")
        if "json" in response.headers.get("content-type", ""):
            return response.json()
        return response.text

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._http.close()

    def __enter__(self) -> "ReadOnlyESClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    @staticmethod
    def _check_path(path: str) -> None:
        if ".." in path or "?" in path or "#" in path:
            raise BlockedRequestError(f"Illegal characters in path: {path}")
        if not any(pattern.match(path) for pattern in ENDPOINT_ALLOWLIST):
            raise BlockedRequestError(f"Endpoint not allowlisted: {path}")

    @staticmethod
    def _build_query(payload: dict[str, Any] | None,
                     params: dict[str, str] | None) -> dict[str, str]:
        query = dict(params or {})
        disallowed = set(query) - QUERY_PARAM_ALLOWLIST
        if disallowed:
            raise BlockedRequestError(f"Query params not allowlisted: {sorted(disallowed)}")
        if payload is not None:
            query["source"] = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
            query["source_content_type"] = "application/json"
        return query

    @staticmethod
    def _guard_request(request: httpx.Request) -> None:
        # Last line of defense: runs inside httpx right before the request is sent.
        if request.method != "GET":
            raise BlockedRequestError(f"Blocked non-GET request: {request.method}")
        if request.content or request.headers.get("content-length", "0") != "0":
            raise BlockedRequestError("Blocked request with a body")
