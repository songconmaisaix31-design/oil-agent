"""Public C repository constructor: Repository(engine, clock=optional_aware_clock).

Every public mutation owns one short PostgreSQL transaction. Services are never
called under these transactions. Trusted operator provisioning is separate from
HTTP authentication; the repository does not import AB or D implementations.
"""

from oil_agent.storage.auth import AuthRepository
from oil_agent.storage.base import RepositoryBase
from oil_agent.storage.decisions import DecisionRepository
from oil_agent.storage.delivery import DeliveryRepository
from oil_agent.storage.ingestion import IngestionRepository
from oil_agent.storage.operations import OperationsRepository
from oil_agent.storage.permissions import PermissionRepository
from oil_agent.storage.queries import QueryRepository


class Repository(
    AuthRepository,
    IngestionRepository,
    DecisionRepository,
    DeliveryRepository,
    QueryRepository,
    OperationsRepository,
    PermissionRepository,
    RepositoryBase,
):
    pass
