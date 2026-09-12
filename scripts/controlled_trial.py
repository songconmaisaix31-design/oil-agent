"""Offline trial deployment preparation and read-only Linux boundary verification.

Never resolves providers, reads credentials, starts containers or applies rules.
Generated firewall commands require separate operator review/execution. This is
an IP/port boundary for current TLS-verifying clients, not a TLS inspection proxy.
"""

import argparse
import ipaddress
import json
import shlex
import ssl
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit

from cryptography import x509

HOSTS = frozenset({"mcp.jin10.com", "api.openai.com", "accounts.feishu.cn", "open.feishu.cn"})
SERVICES = ("api", "ingest", "urgent", "normal")
BRIDGE = "oil-e-trial-eg"
BACKEND = "oil-e-trial-db"
NETWORK = "oil-agent-e-trial-egress"
LABEL = "oil-agent.scope=e-controlled-trial"
OUT, IN, HOST = "OILETRIALOUT", "OILETRIALIN", "OILETRIALHOST"


def validate_pins(value):
    if not isinstance(value, dict) or not set(value).issubset(HOSTS):
        raise ValueError("Only existing adapter hostnames are supported")
    pins = {}
    for host, raw in value.items():
        if not isinstance(raw, str):
            raise ValueError("Each enabled host requires one explicit public IPv4 address")
        try:
            address = ipaddress.ip_address(raw)
        except ValueError:
            raise ValueError("Invalid public IPv4 pin") from None
        if address.version != 4 or not address.is_global or address.is_multicast:
            raise ValueError("Private, reserved, multicast and IPv6 pins are unsupported")
        pins[host] = str(address)
    return dict(sorted(pins.items()))


def firewall_rules(pins):
    addresses = sorted(set(validate_pins(pins).values()))
    rules = {OUT: [], IN: [], HOST: []}
    for address in addresses:
        rules[OUT].append(f"-A {OUT} -d {address}/32 -p tcp -m tcp --dport 443 -j RETURN")
        rules[IN].append(
            f"-A {IN} -s {address}/32 -p tcp -m tcp --sport 443 "
            "-m conntrack --ctstate ESTABLISHED -j RETURN"
        )
    rules[OUT].append(f"-A {OUT} -j DROP")
    rules[IN].append(f"-A {IN} -j DROP")
    rules[HOST] = [
        f"-A {HOST} -m conntrack --ctstate ESTABLISHED -j RETURN",
        f"-A {HOST} -j DROP",
    ]
    return rules


def hooks():
    return {
        "DOCKER-USER": [
            f"-A DOCKER-USER -i {BRIDGE} -j {OUT}",
            f"-A DOCKER-USER -o {BRIDGE} -j {IN}",
        ],
        "INPUT": [f"-A INPUT -i {BRIDGE} -j {HOST}", f"-A INPUT -i {BACKEND} -j {HOST}"],
    }


def firewall_plan(pins):
    lines = [
        "#!/bin/sh",
        "set -eu",
        "# REVIEW ONLY: run on an approved Linux iptables host before creating the network.",
        "# Existing chains cause refusal; no flush/delete/restart is permitted.",
        f"if ip link show dev {BRIDGE} >/dev/null 2>&1; then exit 1; fi",
        "iptables -w 5 -S DOCKER-USER >/dev/null",
    ]
    for chain, rules in firewall_rules(pins).items():
        lines.append(f"iptables -w 5 -N {chain}")
        lines.extend("iptables -w 5 " + rule for rule in rules)
    for chain, rules in hooks().items():
        for rule in reversed(rules):
            lines.append("iptables -w 5 " + rule.replace(f"-A {chain}", f"-I {chain} 1", 1))
    return "\n".join(lines) + "\n"


def read_command(arguments):
    result = subprocess.run(arguments, capture_output=True, text=True, timeout=10)
    if result.returncode:
        # Do not echo Docker daemon errors or full environment/configuration.
        raise ValueError("Boundary inspection unavailable; no deployment authorized")
    return result.stdout


def verify_firewall(pins, read=read_command):
    forward = read(["iptables", "-w", "5", "-S", "FORWARD"]).splitlines()
    forward = [shlex.split(line) for line in forward if line.startswith("-A ")]
    if not forward or forward[0] != ["-A", "FORWARD", "-j", "DOCKER-USER"]:
        raise ValueError("An active first-position Docker iptables user hook is required")
    for chain, expected in firewall_rules(pins).items():
        actual = read(["iptables", "-w", "5", "-S", chain]).splitlines()
        actual = [shlex.split(line) for line in actual if line.startswith("-A ")]
        if actual != [shlex.split(line) for line in expected]:
            raise ValueError("Trial firewall chain differs from the bounded policy")
    for chain, expected in hooks().items():
        actual = read(["iptables", "-w", "5", "-S", chain]).splitlines()
        actual = [shlex.split(line) for line in actual if line.startswith("-A ")]
        if actual[: len(expected)] != [shlex.split(line) for line in expected]:
            raise ValueError("Trial firewall hooks must precede other host rules")


def verify_network(read=read_command):
    values = json.loads(read(["docker", "network", "inspect", NETWORK]))
    if len(values) != 1:
        raise ValueError("Exactly one dedicated trial network required")
    network = values[0]
    if (
        network.get("Name") != NETWORK
        or network.get("Driver") != "bridge"
        or network.get("Internal") is not False
        or network.get("EnableIPv6") is not False
        or network.get("Options", {}).get("com.docker.network.bridge.name") != BRIDGE
        or network.get("Labels", {}).get("oil-agent.scope") != "e-controlled-trial"
    ):
        raise ValueError("Network identity or isolation differs from the trial contract")
    # Pre-start only. Never adopt a network with unknown/existing attachments.
    if network.get("Containers"):
        raise ValueError("Pre-start inspection requires an unattached trial network")


def verify_tls(origin, certificate, key, now=None):
    parsed = urlsplit(origin)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.path
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("An exact HTTPS origin without path or credentials is required")
    certificate, key = Path(certificate), Path(key)
    if not certificate.is_absolute() or not key.is_absolute():
        raise ValueError("TLS paths must be explicit absolute project paths")
    if not certificate.is_file() or not key.is_file():
        raise ValueError("Explicit certificate and key files are required")
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certificate, key)  # Local key pairing; no TLS connection.
    leaf = x509.load_pem_x509_certificate(certificate.read_bytes())
    instant = now or datetime.now(UTC)
    if not leaf.not_valid_before_utc <= instant < leaf.not_valid_after_utc:
        raise ValueError("TLS certificate is outside its validity interval")
    names = leaf.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    if parsed.hostname not in names.get_values_for_type(x509.DNSName):
        raise ValueError("TLS certificate must contain the exact approved DNS hostname")
    # Public trust/chain and phone trust are separate live acceptance gates.


def verify_compose(config, pins, origin, certificate, key):
    """Inspect resolved configuration in memory; never print secret environment values."""
    if config.get("name") != "oil-agent-e-trial":
        raise ValueError("Unexpected Compose project")
    services = config["services"]
    if set(services) != {"postgres", "init", "gateway", *SERVICES}:
        raise ValueError("Unexpected trial services")
    backend = config["networks"]["backend"]
    if (
        backend.get("internal") is not True
        or backend.get("enable_ipv6", False)
        or backend.get("external", False)
        or backend.get("name") != "oil-agent-e-trial_backend"
        or backend.get("driver_opts", {}).get("com.docker.network.bridge.name") != BACKEND
    ):
        raise ValueError("Trial database network must remain internally isolated")
    egress = config["networks"]["trial-egress"]
    if egress.get("external") is not True or egress.get("name") != NETWORK:
        raise ValueError("Compose must attach only the separately inspected egress network")
    database_service = services["postgres"]
    if (
        database_service["environment"].get("POSTGRES_DB") != "oil_e_trial"
        or database_service["environment"].get("POSTGRES_USER") != "oil_e_trial"
        or config["volumes"]["trial-data"].get("name") != "oil-agent-e-trial_trial-data"
        or config["volumes"]["trial-data"].get("external")
        or config["volumes"]["trial-data"].get("driver_opts")
    ):
        raise ValueError("A separate trial database and project volume are required")
    volumes = database_service.get("volumes", [])
    if (
        len(volumes) != 1
        or volumes[0].get("type") != "volume"
        or volumes[0].get("source") != "trial-data"
        or volumes[0].get("target") != "/var/lib/postgresql/data"
    ):
        raise ValueError("Existing data volumes must never be attached to the trial")
    for name, service in services.items():
        if service.get("network_mode") or service.get("privileged"):
            raise ValueError("Host networking and privilege are unsupported")
        if service.get("entrypoint") or service.get("cap_add"):
            raise ValueError("Entry point replacement and added capabilities are unsupported")
        if "no-new-privileges:true" not in service.get("security_opt", []):
            raise ValueError("Existing privilege restriction must be preserved")
        if name != "postgres" and (
            service.get("read_only") is not True
            or service.get("cap_drop") != ["ALL"]
            or not service.get("mem_limit")
            or not service.get("pids_limit")
        ):
            raise ValueError("Existing filesystem, capability and resource bounds are required")
        expected_networks = {"backend", "trial-egress"} if name in SERVICES else {"backend"}
        if set(service["networks"]) != expected_networks:
            raise ValueError("Unexpected trial network attachment")
        if name != "gateway" and service.get("ports"):
            raise ValueError("Only the loopback TLS gateway may publish a port")
        if name in SERVICES:
            if service.get("extra_hosts", {}) != {host: [ip] for host, ip in pins.items()}:
                raise ValueError("Effective DNS pins differ from the reviewed IP set")
            if service.get("dns") != ["127.0.0.1"]:
                raise ValueError("Recursive external DNS is unsupported")
            if service.get("sysctls", {}).get("net.ipv6.conf.all.disable_ipv6") != "1":
                raise ValueError("IPv6 must remain disabled")
        if name in (*SERVICES, "init"):
            command = (
                ["worker", "--queue", name] if name in ("ingest", "urgent", "normal") else [name]
            )
            if (
                service.get("command") != command
                or service.get("volumes")
                or service.get("image") != services["api"].get("image")
            ):
                raise ValueError(
                    "Shared application image, command and unmodified runtime required"
                )
            environment = service["environment"]
            if (
                environment.get("OIL_RUNTIME_FACTORY") != "oil_agent.bootstrap:build_runtime"
                or environment.get("OIL_ASGI_FACTORY") != "oil_agent.bootstrap:create_app"
            ):
                raise ValueError("Only the accepted shared runtime/API factories are supported")
            database = urlsplit(environment["OIL_DATABASE_URL"])
            if (
                database.scheme != "postgresql+psycopg"
                or database.hostname != "postgres"
                or database.port not in (None, 5432)
                or database.username != "oil_e_trial"
                or database.path != "/oil_e_trial"
                or database.query
                or database.fragment
            ):
                raise ValueError("Database URL must use only the new isolated trial database")
            if not database.password or unquote(database.password) != database_service[
                "environment"
            ].get("POSTGRES_PASSWORD"):
                raise ValueError("Explicit trial database credential injection must match")
            if (
                environment.get("OIL_DATA_PROVENANCE") != "trial"
                or environment.get("OIL_ENVIRONMENT") != "test"
                or environment.get("OIL_FIXTURE_DATASET") != "null"
                or environment.get("OIL_OUTBOUND_MODE") not in ("dry_run", "trial")
                or environment.get("OIL_COOKIE_SECURE") != "true"
                or environment.get("OIL_PUBLIC_ORIGIN") != origin
            ):
                raise ValueError("Trial provenance, HTTPS or outbound scope mismatch")
            if any(
                environment.get(key) != "false"
                for key in ("OIL_SMS_ENABLED", "OIL_PHONE_ENABLED", "OIL_REMINDERS_ENABLED")
            ):
                raise ValueError("Additional notification paths must remain disabled")
            required = set()
            if environment.get("OIL_EXTERNAL_SOURCES_ENABLED") == "true":
                required.add("mcp.jin10.com")
            if environment.get("OIL_MODEL_CALLS_ENABLED") == "true":
                required.add("api.openai.com")
            if environment.get("OIL_IDENTITY_ENABLED") == "true":
                required.update(("accounts.feishu.cn", "open.feishu.cn"))
            if environment.get("OIL_OUTBOUND_MODE") == "trial":
                required.add("open.feishu.cn")
            if set(pins) != required:
                raise ValueError("Pins must exactly match the enabled adapter capabilities")
    ports = services["gateway"].get("ports", [])
    if (
        len(ports) != 1
        or ports[0].get("host_ip") != "127.0.0.1"
        or ports[0].get("target") != 8443
        or str(ports[0].get("published")) != "18443"
    ):
        raise ValueError("Gateway must bind only the assigned loopback TLS port")
    mounts = {mount["target"]: mount for mount in services["gateway"]["volumes"]}
    for target, path in (("/run/oil-tls/cert.pem", certificate), ("/run/oil-tls/key.pem", key)):
        mount = mounts.get(target, {})
        if (
            mount.get("type") != "bind"
            or not mount.get("read_only")
            or Path(mount.get("source", "")) != Path(path)
            or mount.get("bind", {}).get("create_host_path") is not False
        ):
            raise ValueError("TLS mount must use the exact inspected read-only file")


def prepare(pins, directory):
    pins = validate_pins(pins)
    directory = Path(directory)
    directory.mkdir(mode=0o700, parents=False, exist_ok=False)
    # JSON is also valid YAML; all host values are validated nonsecret public IPs.
    fragment = {"services": {name: {"extra_hosts": pins} for name in SERVICES}}
    (directory / "trial-pins.yaml").write_text(json.dumps(fragment, indent=2) + "\n")
    (directory / "trial-firewall.sh").write_text(firewall_plan(pins), newline="\n")


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("Duplicate network configuration key")
        value[key] = item
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "check"), nargs="?", default="check")
    parser.add_argument("--pins", type=Path, required=True, help="Explicit nonsecret host/IP JSON")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--origin")
    parser.add_argument("--tls-cert", type=Path)
    parser.add_argument("--tls-key", type=Path)
    parser.add_argument("--env-file", type=Path, help="Explicit project-scoped Compose injection")
    parser.add_argument("--pins-overlay", type=Path)
    args = parser.parse_args()
    try:
        pins = validate_pins(json.loads(args.pins.read_text(), object_pairs_hook=unique_object))
        if args.action == "prepare":
            if args.output_dir is None:
                raise ValueError("An explicit new output directory is required")
            prepare(pins, args.output_dir)
            print("Prepared nonsecret configuration only; nothing activated")
        else:
            if not all(
                (args.origin, args.tls_cert, args.tls_key, args.env_file, args.pins_overlay)
            ):
                raise ValueError("TLS and explicit project Compose inputs are prerequisites")
            verify_tls(args.origin, args.tls_cert, args.tls_key)
            root = Path(__file__).resolve().parents[1]
            if not args.env_file.is_absolute() or not args.pins_overlay.is_absolute():
                raise ValueError("Explicit absolute configuration paths required")
            raw = read_command(
                [
                    "docker",
                    "compose",
                    "--env-file",
                    str(args.env_file),
                    "--project-name",
                    "oil-agent-e-trial",
                    "--profile",
                    "controlled-trial",
                    "--file",
                    str(root / "deploy/compose.yaml"),
                    "--file",
                    str(root / "deploy/compose.e-trial.yaml"),
                    "--file",
                    str(args.pins_overlay),
                    "config",
                    "--format",
                    "json",
                ]
            )
            verify_compose(json.loads(raw), pins, args.origin, args.tls_cert, args.tls_key)
            verify_firewall(pins)
            verify_network()
            print("Pre-start IPv4 boundaries match; live TLS/provider acceptance still pending")
    except (
        ValueError,
        OSError,
        KeyError,
        TypeError,
        x509.ExtensionNotFound,
        subprocess.SubprocessError,
    ):
        parser.exit(
            1, "Trial preparation/check refused; inspect the explicit nonsecret inputs and host\n"
        )


if __name__ == "__main__":
    main()
