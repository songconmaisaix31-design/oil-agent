"""Regenerate the sole mobile schema artifact from the Python app, offline.

Run ``uv run python -m oil_agent.api.export_openapi``. No environment settings,
secret reads, network calls, authentication or database connection are needed.
"""

import json
from pathlib import Path

from oil_agent.api.app import create_app
from oil_agent.runtime.settings import Settings


def schema() -> dict:
    return create_app(Settings.model_construct()).openapi()


def main() -> None:
    target = Path(__file__).parents[1] / "contracts" / "openapi.json"
    target.write_text(json.dumps(schema(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Generated {target.name}")


if __name__ == "__main__":
    main()
