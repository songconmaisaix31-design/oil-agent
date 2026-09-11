"""ASGI factory for ``uv run uvicorn oil_agent.bootstrap:create_app --factory``.

C foundation owns this seam; later integration supplies AB services and D
channels through their contracts. Importing it does not create an application.
"""

from oil_agent.api.app import create_app

__all__ = ["create_app"]
