"""ASGI factory for ``uv run uvicorn oil_agent.bootstrap:create_app --factory``.

C owns this seam; integration supplies AB services and D channels through
OIL_RUNTIME_FACTORY=module:function. Importing it does not create an application.
"""

from oil_agent.api.app import create_app as api_factory
from oil_agent.runtime.cli import load_runtime
from oil_agent.runtime.settings import Settings


def create_app():
    settings = Settings()
    runtime = load_runtime(settings) if settings.database_url else None
    return api_factory(settings, runtime=runtime)


__all__ = ["create_app"]
