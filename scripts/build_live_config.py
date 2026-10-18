"""Build validated live permissions and rules JSON from one reviewed spec.

Usage::

    uv run --locked python scripts/build_live_config.py \
      --spec private/live-spec.json --output-dir private/generated

The spec is operator-authored and contains identifiers, never credentials. The
command writes ``sources.json``, ``model.json``, ``identity.json``,
``trial_send.json``, ``rules.json`` and an ``env.generated`` fragment. Every
object is validated by the same pydantic models the runtime uses, so a generated
file either matches the contract or fails here.

Spec fields (``mode`` is ``trial`` or ``production``)::

    {
      "mode": "trial",
      "valid_from": "2026-10-18T00:00:00Z",
      "expires_at": "2026-11-17T00:00:00Z",
      "authorization_ref": "op:oil-2026-10",
      "rules_path": "config/oil-event-rules.example.json",
      "sources": [
        {"source_id": "eia-wti", "provider": "eia", "host": "api.eia.gov",
         "max_requests": 24, "rights_ref": "public:eia-api"}
      ],
      "model": {"provider": "deepseek", "model": "deepseek-flash",
                "max_requests": 50, "max_tokens": 200000},
      "identity": {
        "app_id": "cli_xxx", "tenant_key": "tnt_xxx",
        "recipients": [
          {"actor_id": "u-self", "recipient_id": "self", "open_id": "ou_xxx"}
        ]
      },
      "trial_send": {
        "recipient_ids": ["self"],
        "first_report_policy": "credible_single_source",
        "allow_reports": true
      }
    }

``identity``/``trial_send`` are omitted for source/model-only dry-run rehearsal.
"""

import argparse
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from oil_agent.intelligence.rules import ApprovedRules
from oil_agent.runtime.permissions import (
    ApprovedIdentity,
    IdentityPermission,
    ModelPermission,
    SourcePermission,
    TrialSendPermission,
)

CREDENTIAL_REFS = {
    "eia": "project:eia",
    "gnews": "project:gnews",
}
MODEL_CREDENTIAL_REF = "project:deepseek"


def _permission(spec, approval_id, *, max_requests):
    return {
        "approval_id": approval_id,
        "authorization_ref": spec["authorization_ref"],
        "valid_from": spec["valid_from"],
        "expires_at": spec["expires_at"],
        "budget_ref": spec.get("budget_ref", "project:oil-no-new-fee"),
        "max_requests": max_requests,
    }


def build(spec: dict, base: Path):
    now = datetime.now(UTC)
    valid_from = spec.get("valid_from") or now.isoformat()
    expires_at = spec.get("expires_at") or (now + timedelta(days=28)).isoformat()
    spec = spec | {"valid_from": valid_from, "expires_at": expires_at}

    rules_path = base / spec["rules_path"]
    raw_rules = json.loads(rules_path.read_text(encoding="utf-8"))
    raw_rules["provenances"] = [spec["mode"]]
    rules = ApprovedRules.model_validate(raw_rules)
    if not (
        rules.valid_from <= datetime.fromisoformat(valid_from)
        and rules.expires_at >= datetime.fromisoformat(expires_at)
    ):
        raise SystemExit("Permission window must fit within the loaded rule approval")
    reference = f"{rules.authorization_ref}@{rules.version}"

    sources = []
    # A source approval is capped at thirty days by the permission contract; the
    # operator renews it monthly while model/identity approvals may run longer.
    source_expires = min(
        datetime.fromisoformat(expires_at),
        datetime.fromisoformat(valid_from) + timedelta(days=29),
    )
    source_spec = spec | {"expires_at": source_expires.isoformat()}
    for item in spec["sources"]:
        permission = SourcePermission(
            **_permission(
                source_spec, f"source-{item['source_id']}", max_requests=item["max_requests"]
            ),
            source_id=item["source_id"],
            provider=item["provider"],
            rights_ref=item["rights_ref"],
            credentials_ref=CREDENTIAL_REFS[item["provider"]],
            host=item["host"],
        )
        sources.append(permission)

    model = ModelPermission(
        **_permission(spec, "model-deepseek", max_requests=spec["model"]["max_requests"]),
        provider=spec["model"]["provider"],
        model=spec["model"]["model"],
        credentials_ref=MODEL_CREDENTIAL_REF,
        rules_ref=reference,
        max_tokens=spec["model"]["max_tokens"],
    )

    identity = None
    if spec.get("identity"):
        entries = spec["identity"]
        identities = tuple(
            ApprovedIdentity(
                actor_id=item["actor_id"],
                recipient_id=item["recipient_id"],
                subject=f"{entries['tenant_key']}:{entries['app_id']}:{item['open_id']}",
                role=item.get("role", "viewer"),
            )
            for item in entries["recipients"]
        )
        identity = IdentityPermission(
            **_permission(
                spec, "identity-feishu", max_requests=spec["identity"].get("max_requests", 100)
            ),
            app_id=entries["app_id"],
            tenant_key=entries["tenant_key"],
            credentials_ref="project:feishu",
            identities=identities,
        )

    trial_send = None
    if spec.get("trial_send"):
        send = spec["trial_send"]
        trial_send = TrialSendPermission(
            **_permission(spec, "send-feishu", max_requests=send.get("max_requests", 200)),
            recipient_ids=tuple(send["recipient_ids"]),
            rules_ref=reference,
            first_report_policy=send["first_report_policy"],
            allow_reports=send.get("allow_reports", True),
        )
        if identity is None:
            raise SystemExit("A trial send permission requires an identity permission")
        approved = {item.recipient_id for item in identity.identities}
        if not set(trial_send.recipient_ids) <= approved:
            raise SystemExit("Trial recipients must be inside the approved identity scope")

    return sources, model, identity, trial_send, rules


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--root", default=".")
    args = parser.parse_args(argv)
    base = Path(args.root).resolve()
    spec = json.loads((base / args.spec).read_text(encoding="utf-8"))
    sources, model, identity, trial_send, rules = build(spec, base)
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)

    def write(name, value):
        """Write a readable file and return its compact single-line form."""
        pretty = json.dumps(value, ensure_ascii=False, indent=2)
        (output / name).write_text(pretty, encoding="utf-8")
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))

    sources_payload = [item.model_dump(mode="json") for item in sources]
    env = {
        "OIL_SOURCE_PERMISSIONS": write("sources.json", sources_payload),
        "OIL_MODEL_PERMISSION": write("model.json", model.model_dump(mode="json")),
        "OIL_APPROVED_RULES_JSON": write("rules.json", rules.model_dump(mode="json")),
    }
    if identity is not None:
        env["OIL_IDENTITY_PERMISSION"] = write("identity.json", identity.model_dump(mode="json"))
    if trial_send is not None:
        env["OIL_TRIAL_SEND_PERMISSION"] = write(
            "trial_send.json", trial_send.model_dump(mode="json")
        )
    lines = ["# Generated non-secret configuration; inject credentials separately."]
    for key, value in env.items():
        lines.append(f"{key}={value}")
    (output / "env.generated").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"WROTE {len(env)} fields to {output}")
    print(f"RULE_REF {rules.authorization_ref}@{rules.version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
