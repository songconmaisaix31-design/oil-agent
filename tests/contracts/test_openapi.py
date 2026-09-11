"""Mobile schema stays generated from exactly the Python API definitions."""

import json
from pathlib import Path

from oil_agent.api.export_openapi import schema


def test_generated_openapi_is_current():
    committed = Path("src/oil_agent/contracts/openapi.json")
    assert json.loads(committed.read_text(encoding="utf-8")) == schema()


def test_mobile_paths_have_auth_and_explicit_placeholder_status():
    paths = schema()["paths"]
    for path in (
        "/api/v1/events",
        "/api/v1/events/{event_id}",
        "/api/v1/events/{event_id}/ack",
        "/api/v1/events/{event_id}/feedback",
        "/api/v1/reports",
        "/api/v1/quotes/preview",
        "/api/v1/quotes/import",
        "/api/v1/config",
        "/api/v1/status",
        "/api/v1/session",
    ):
        assert path in paths
        for method, operation in paths[path].items():
            assert "501" in operation["responses"]
            if not (path == "/api/v1/session" and method == "post"):
                assert operation["security"] == [{"APIKeyCookie": []}]
