"""Static deployment boundaries, separate from container/application acceptance."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_database_is_internal_and_only_gateway_publishes_loopback():
    config = yaml.safe_load((ROOT / "deploy/compose.yaml").read_text())
    assert config["name"] == "oil-agent-e"
    assert config["networks"]["backend"]["internal"] is True
    for name, service in config["services"].items():
        if name == "gateway":
            assert all(port.startswith("127.0.0.1:") for port in service["ports"])
        else:
            assert not service.get("ports"), name
            assert service["networks"] == ["backend"], name
    override = yaml.safe_load((ROOT / "deploy/compose.e-test.yaml").read_text())
    assert override["services"]["postgres"]["ports"] == ["127.0.0.1:55434:5432"]


def test_one_application_image_safe_defaults_and_explicit_initialization():
    config = yaml.safe_load((ROOT / "deploy/compose.yaml").read_text())
    services = config["services"]
    shared = config["x-app"]["environment"]
    defaults = {
        "OIL_ENVIRONMENT": "test",
        "OIL_OUTBOUND_MODE": "dry_run",
        "OIL_DATA_PROVENANCE": "fixture",
        "OIL_FIXTURE_DATASET": "local-v01",
        "OIL_EXTERNAL_SOURCES_ENABLED": "false",
        "OIL_MODEL_CALLS_ENABLED": "false",
        "OIL_IDENTITY_ENABLED": "false",
        "OIL_SOURCE_PERMISSIONS": "[]",
        "OIL_MODEL_PERMISSION": "null",
        "OIL_IDENTITY_PERMISSION": "null",
        "OIL_TRIAL_SEND_PERMISSION": "null",
        "OIL_DAILY_MODEL_CALLS": "0",
        "OIL_DAILY_MODEL_TOKENS": "0",
    }
    for key, default in defaults.items():
        assert shared[key] == "${" + key + ":-" + default + "}"
    for key in (
        "OIL_JIN10_TOKEN",
        "OIL_OPENAI_API_KEY",
        "OIL_FEISHU_APP_SECRET",
        "OIL_FEISHU_ENCRYPT_KEY",
        "OIL_FEISHU_VERIFICATION_TOKEN",
    ):
        assert shared[key] == "${" + key + ":-}"
    assert shared["OIL_DATABASE_URL"].startswith("${OIL_DATABASE_URL:?")
    assert services["postgres"]["environment"]["POSTGRES_PASSWORD"].startswith(
        "${OIL_POSTGRES_PASSWORD:?"
    )
    assert shared["OIL_COOKIE_SECURE"] == "true"
    image = services["api"]["image"]
    for name in ("api", "init", "ingest", "urgent", "normal"):
        service = services[name]
        assert service["image"] == image
        # Parsed YAML resolves the application anchor. Every queue/API/init must
        # inherit the entire permission, factory and credential environment.
        assert service["environment"] == shared
        for key in ("OIL_REMINDERS_ENABLED", "OIL_SMS_ENABLED", "OIL_PHONE_ENABLED"):
            assert service["environment"][key] == "false"
        assert service["read_only"] is True
        assert service["cap_drop"] == ["ALL"]
        assert service["mem_limit"] and service["pids_limit"]
        if name != "init":
            assert service["depends_on"]["init"]["condition"] == "service_completed_successfully"
    for queue in ("ingest", "urgent", "normal"):
        assert services[queue]["command"] == ["worker", "--queue", queue]


def test_reverse_proxy_preserves_api_path_and_disables_sensitive_access_log():
    text = (ROOT / "deploy/nginx.conf").read_text()
    assert "location /api/" in text
    assert "proxy_pass http://api:8000;" in text
    assert "access_log off;" in text
    assert "listen 8080;" in text
    assert "try_files $uri $uri/ /index.html;" in text


def test_backup_restore_do_not_overwrite_or_delete_existing_state():
    backup = (ROOT / "scripts/backup.sh").read_text()
    restore = (ROOT / "scripts/restore-isolated.sh").read_text()
    scope = (ROOT / "scripts/compose_scope.sh").read_text()
    assert "set -C" in backup
    assert "--format=custom" in backup
    assert "--single-transaction" in restore
    assert restore.index("createdb --username") < restore.index('--dbname="$oil_restore"')
    assert "oil_e_restore_" in restore
    assert "com.docker.compose.project" in scope and "com.docker.compose.service" in scope
    for text in (backup, restore, scope):
        assert "--clean" not in text
        assert "dropdb" not in text
        assert "volume rm" not in text
        assert " down" not in text
    assert "--env-file" in scope  # Never auto-read a pre-existing repository .env.
