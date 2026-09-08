"""Shared pytest configuration for the peritype test suite."""

from collections.abc import Iterator

import pytest

from peritype.utils import use_cache
from peritype.utils._cache import CACHE


@pytest.fixture(autouse=True)
def isolated_cache() -> Iterator[None]:
    """Give every test a fresh, enabled wrap cache.

    The cache is a process-wide singleton. Without this fixture a wrap built (or poisoned) by one
    test would be visible to the next one, making failures order-dependent.
    """
    CACHE.twrap_cache.clear()
    CACHE.fwrap_cache.clear()
    use_cache(True)
    yield
    CACHE.twrap_cache.clear()
    CACHE.fwrap_cache.clear()
    use_cache(True)


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Turn ``@pytest.mark.known_bug("reason")`` into a strict xfail.

    A ``known_bug`` test describes the behaviour the library *should* have. While the defect exists
    the test fails and is reported as xfail. Once the defect is fixed the test passes, the strict
    xfail turns that into a hard failure, and the marker must be removed. This keeps the spec and
    the bug list in the same place and stops fixed bugs from staying flagged.
    """
    for item in items:
        for marker in item.iter_markers("known_bug"):
            reason = marker.kwargs.get("reason") or (marker.args[0] if marker.args else "known bug")
            condition = marker.kwargs.get("condition", True)
            item.add_marker(pytest.mark.xfail(condition, strict=True, reason=reason))
