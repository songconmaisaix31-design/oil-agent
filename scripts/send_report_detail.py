"""Send the full daily evidence appendix as a Feishu file, once per report date.

The short Feishu message carries only the conclusion. This command renders the
full report (facts, evidence excerpts, metrics, watch items, gaps, sources) to a
Markdown file and uploads it to the approved recipients. A marker file prevents
duplicate uploads for the same report date.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
import psycopg

from oil_agent.contracts.dto import Report, SourceRecord
from oil_agent.runtime.settings import Settings
from oil_agent.storage.notification_text import report_detail_markdown

API = "https://open.feishu.cn/open-apis"
SHANGHAI = ZoneInfo("Asia/Shanghai")


def _latest_report(conn) -> Report | None:
    intent = conn.execute(
        "select subject_id, revision from notification_intents "
        "where kind = 'daily_report' order by created_at desc limit 1"
    ).fetchone()
    if not intent:
        return None
    row = conn.execute(
        "select payload from subject_versions where subject_id = %s and revision = %s",
        (intent[0], intent[1]),
    ).fetchone()
    return Report.model_validate(row[0]) if row else None


def _records(conn, report: Report) -> dict:
    records = {}
    for ref in report.evidence:
        row = conn.execute(
            "select payload from source_records where record_id = %s and revision = %s",
            (ref.record_id, ref.revision),
        ).fetchone()
        if row:
            records[(ref.record_id, ref.revision)] = SourceRecord.model_validate(row[0])
    return records


def _token(app_id: str, app_secret: str) -> str:
    response = httpx.post(
        f"{API}/auth/v3/tenant_access_token/internal",
        json={"app_id": app_id, "app_secret": app_secret},
        trust_env=False,
        timeout=20,
    )
    data = response.json()
    if response.status_code != 200 or data.get("code") != 0:
        raise SystemExit(f"TOKEN_FAIL {response.status_code} {data.get('code')}")
    return data["tenant_access_token"]


def _upload(token: str, name: str, content: bytes) -> str:
    response = httpx.post(
        f"{API}/im/v1/files",
        headers={"Authorization": f"Bearer {token}"},
        data={"file_type": "stream", "file_name": name},
        files={"file": (name, content)},
        trust_env=False,
        timeout=30,
    )
    data = response.json()
    if response.status_code != 200 or data.get("code") != 0:
        raise SystemExit(f"UPLOAD_FAIL {response.status_code} {data.get('code')} {data.get('msg')}")
    return data["data"]["file_key"]


def _send_file(token: str, open_id: str, file_key: str) -> str | None:
    response = httpx.post(
        f"{API}/im/v1/messages",
        params={"receive_id_type": "open_id"},
        headers={"Authorization": f"Bearer {token}"},
        json={
            "receive_id": open_id,
            "msg_type": "file",
            "content": json.dumps({"file_key": file_key}, separators=(",", ":")),
        },
        trust_env=False,
        timeout=20,
    )
    data = response.json()
    if response.status_code != 200 or data.get("code") != 0:
        raise SystemExit(f"SEND_FAIL {response.status_code} {data.get('code')} {data.get('msg')}")
    return data.get("data", {}).get("message_id")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    settings = Settings()
    if settings.database_url is None:
        print("NO_DATABASE_URL")
        return 2
    directory = Path(os.environ.get("OIL_DETAIL_DIR", "details"))
    directory.mkdir(parents=True, exist_ok=True)

    with psycopg.connect(settings.database_url.get_secret_value().replace("+psycopg", "")) as conn:
        report = _latest_report(conn)
        if report is None:
            print("NO_REPORT")
            return 0
        if report.report_date != datetime.now(SHANGHAI).date():
            print(f"NO_REPORT_TODAY latest={report.report_date}")
            return 0
        marker = directory / f"{report.report_date.isoformat()}.sent"
        if marker.exists() and not args.force:
            print(f"ALREADY_SENT {marker}")
            return 0
        records = _records(conn, report)
        detail = report_detail_markdown(report, records)
        path = directory / f"{report.report_date.isoformat()}-oil-agent-detail.md"
        path.write_text(detail, encoding="utf-8")
        print(f"WROTE {path} {len(detail)} chars")

    permission = json.loads(os.environ["OIL_IDENTITY_PERMISSION"])
    app_secret = os.environ["OIL_FEISHU_APP_SECRET"]
    token = _token(permission["app_id"], app_secret)
    file_key = _upload(token, path.name, path.read_bytes())
    print(f"UPLOADED {file_key}")
    for identity in permission["identities"]:
        open_id = identity["subject"].rsplit(":", 1)[-1]
        message_id = _send_file(token, open_id, file_key)
        print(f"SENT {identity['recipient_id']} {message_id}")
    marker.write_text(datetime.now(SHANGHAI).isoformat(), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
