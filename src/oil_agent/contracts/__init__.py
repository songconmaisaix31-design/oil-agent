"""Frozen v0.1 shared contracts for AB, C and D.

Import DTOs from ``oil_agent.contracts.dto``, API envelopes from ``.http`` and
the five async service interfaces from ``.services``. Only C owns these files.
Python models are authoritative; generate mobile OpenAPI with
``uv run python -m oil_agent.api.export_openapi``. Schema changes require a
coordinator handoff; consumers must not duplicate or relax these definitions.
"""

CONTRACT_VERSION = "0.1.0"
