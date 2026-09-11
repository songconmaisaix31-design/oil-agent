"""ASGI factory for ``uv run uvicorn oil_agent.bootstrap:create_app --factory``.

API and workers share the safe runtime factory. A trusted OIL_RUNTIME_FACTORY
override remains explicit; importing this module creates no application or data.
"""

from oil_agent.api.app import create_app as api_factory
from oil_agent.channels import DryRunChannel
from oil_agent.ingestion import SafeQuoteParser
from oil_agent.intelligence import ConservativeAssessmentService
from oil_agent.reporting import SnapshotReportService
from oil_agent.runtime.cli import load_runtime
from oil_agent.runtime.service import Runtime, RuntimeServices
from oil_agent.runtime.settings import Settings
from oil_agent.storage.database import create_db_engine
from oil_agent.storage.repository import Repository


def build_runtime(settings: Settings) -> Runtime:
    """Wire existing local services without sources, identities or seeded data."""
    repository = Repository(create_db_engine(settings))
    return Runtime(
        repository,
        RuntimeServices(
            assessment=ConservativeAssessmentService(clock=repository.clock),
            reports=SnapshotReportService(clock=repository.clock),
            quote_parser=SafeQuoteParser(),
            channels={"dry_run": DryRunChannel()},
        ),
        settings=settings,
    )


def create_app():
    settings = Settings()
    runtime = load_runtime(settings) if settings.database_url else None
    return api_factory(settings, runtime=runtime)


__all__ = ["build_runtime", "create_app"]
