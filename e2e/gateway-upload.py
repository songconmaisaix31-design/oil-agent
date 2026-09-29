"""Check the actual nginx/API raw upload boundary using only synthetic CSV bytes."""

import base64
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:18084"


def main():
    seed = json.loads(Path(os.environ["OIL_E_SESSION_FILE"]).read_text())
    assert seed["is_fixture"] and seed["dataset"] == "synthetic-e-runtime"
    headers = {"Cookie": "oil_session=" + seed["sessions"]["admin"]}
    session = json.load(
        urllib.request.urlopen(
            urllib.request.Request(
                BASE + "/api/v1/session",
                headers=headers,
            ),
            timeout=5,
        )
    )
    headers.update(
        {"Content-Type": "application/json", "x-csrf-token": session["csrf_token"], "Origin": BASE}
    )
    columns = ["value", "as_of", *["unused" + str(i) for i in range(62)]]
    line = ",".join(["1234.50", "2026-09-11T00:00:00Z", *(["x" * 1990] * 62)]) + "\n"
    data = (",".join(columns) + "\n" + line * 16).encode()
    assert 1_900_000 < len(data) <= 2_000_000
    results = []
    for raw, expected in ((data, 200), (b"x" * 2_000_001, 422)):
        payload = {
            "filename": "e-boundary.csv",
            "media_type": "text/csv",
            "content_base64": base64.b64encode(raw).decode(),
            "field_mapping": {"value": "value", "as_of": "as_of"},
            "rights_ref": "fixture:original-synthetic-E-boundary",
        }
        request = urllib.request.Request(
            BASE + "/api/v1/quotes/preview", headers=headers, data=json.dumps(payload).encode()
        )
        try:
            response = urllib.request.urlopen(request, timeout=25)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            assert response.status == expected, (len(raw), response.status)
            assert response.headers["Cache-Control"] == "no-store"
            results.append({"raw_bytes": len(raw), "status": response.status})
    print(json.dumps({"is_fixture": True, "gateway_upload": results}))


if __name__ == "__main__":
    main()
