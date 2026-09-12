"""Run C's unchanged C1 assertions on E's guarded, migrated synthetic database."""

import pytest
from unit.storage import test_c1_storage as _original

pytestmark = _original.pytestmark
c1 = _original.c1

# Keep the original functions, helpers, assertions and parametrization together.
globals().update(
    {name: value for name, value in vars(_original).items() if name.startswith("test_")}
)


@pytest.fixture
def repository(e_repository):
    # E migrations seed BusinessConfig; the original c1 fixture freezes this clock.
    # This module-local alias leaves C's own database guard and other tests intact.
    return e_repository
