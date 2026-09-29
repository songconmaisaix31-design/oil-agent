"""Actual offline Compose rendering; no daemon, database or provider operations."""

import json
import os
import subprocess
from pathlib import Path
from uuid import uuid4

import pytest

ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ROOT / "deploy/compose.c1-db.yaml"
PROJECT = "oil-agent-feishu-trial"
IMAGE = "postgres:16-alpine@sha256:e013e867e712fec275706a6c51c966f0bb0c93cfa8f51000f85a15f9865a28cb"


@pytest.fixture(scope="module")
def compose_runner(tmp_path_factory):
    directory = tmp_path_factory.mktemp("synthetic-c1-db-compose")
    environment = {
        key: os.environ[key]
        for key in ("PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP")
        if key in os.environ
    }
    environment["DOCKER_CONFIG"] = str(directory / "empty-docker-config")

    def render(password=None):
        assert COMPOSE.is_file(), "Standalone C1 database-only Compose definition is missing"
        child_environment = dict(environment)
        if password is not None:
            child_environment["OIL_C1_DB_PASSWORD"] = password
        return subprocess.run(
            (["docker-compose"] if os.name == "nt" else ["docker", "compose"])
            + [
                "--env-file",
                str(ROOT / "deploy/compose.env"),
                "--file",
                str(COMPOSE),
                "config",
                "--format",
                "json",
            ],
            env=child_environment,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )

    return render


@pytest.fixture(scope="module")
def rendered(compose_runner):
    password = "synthetic-" + uuid4().hex
    result = compose_runner(password)
    assert result.returncode == 0, "Synthetic C1 Compose rendering failed (output withheld)"
    try:
        config = json.loads(result.stdout)
    except ValueError:
        pytest.fail("C1 Compose did not return JSON (output withheld)")
    # Compare only in memory, then remove the synthetic value before other assertions.
    actual = config["services"]["postgres"]["environment"].pop("POSTGRES_PASSWORD", None)
    if actual != password:
        pytest.fail("C1 password interpolation mismatch (values withheld)")
    return config


def test_standalone_database_has_no_application_or_activation_services(rendered):
    assert rendered["name"] == PROJECT
    assert set(rendered["services"]) == {"postgres"}
    postgres = rendered["services"]["postgres"]
    assert postgres["image"] == IMAGE
    assert postgres["environment"] == {
        "POSTGRES_DB": "oil_c1_trial",
        "POSTGRES_USER": "oil_c1_trial",
        "TZ": "UTC",
    }
    for key in ("build", "entrypoint", "depends_on", "env_file", "privileged", "cap_add"):
        assert not postgres.get(key), key
    assert postgres["restart"] == "no"
    assert postgres["security_opt"] == ["no-new-privileges:true"]
    assert postgres["labels"] == {
        "oil-agent.scope": "feishu-c1",
        "oil-agent.data-provenance": "fixture",
        "oil-agent.fixture-dataset": "feishu-c1",
    }


def test_only_assigned_loopback_port_and_internal_project_network(rendered):
    postgres = rendered["services"]["postgres"]
    assert not postgres.get("network_mode")
    assert set(postgres["networks"]) == {"backend"}
    assert len(postgres["ports"]) == 1
    port = postgres["ports"][0]
    assert (port["host_ip"], str(port["published"]), port["target"], port["protocol"]) == (
        "127.0.0.1",
        "55436",
        5432,
        "tcp",
    )
    assert set(rendered["networks"]) == {"backend"}
    network = rendered["networks"]["backend"]
    assert network["name"] == PROJECT + "_backend"
    assert network["internal"] is True
    assert not network.get("external")
    assert not network.get("enable_ipv6")


def test_only_new_project_volume_and_bounded_postgres_settings(rendered):
    assert set(rendered["volumes"]) == {"c1-data"}
    volume = rendered["volumes"]["c1-data"]
    assert volume["name"] == PROJECT + "_c1-data"
    assert not volume.get("external")
    assert not volume.get("driver_opts")
    postgres = rendered["services"]["postgres"]
    assert len(postgres["volumes"]) == 1
    mount = postgres["volumes"][0]
    assert (mount["type"], mount["source"], mount["target"]) == (
        "volume",
        "c1-data",
        "/var/lib/postgresql/data",
    )
    assert postgres["command"] == [
        "postgres",
        "-c",
        "timezone=UTC",
        "-c",
        "max_connections=40",
        "-c",
        "shared_buffers=32MB",
    ]
    assert postgres["healthcheck"]["test"] == [
        "CMD-SHELL",
        "pg_isready -U oil_c1_trial -d oil_c1_trial",
    ]
    assert postgres["pids_limit"] == 64
    assert int(postgres["mem_limit"]) == 128 * 1024 * 1024
    assert float(postgres["cpus"]) == 0.5
    assert postgres["logging"]["options"] == {"max-size": "5m", "max-file": "2"}


@pytest.mark.parametrize("password", [None, ""], ids=["missing", "empty"])
def test_compose_refuses_missing_process_password(compose_runner, password):
    result = compose_runner(password)
    assert result.returncode != 0
    assert "OIL_C1_DB_PASSWORD" in result.stderr
    assert not result.stdout.strip(), "Failed rendering must not emit resolved environment"
