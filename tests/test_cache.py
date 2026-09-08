"""The process-wide wrap cache: identity, ``use_cache``, and weak references."""

import gc
from typing import Annotated

from peritype import wrap_func, wrap_type
from peritype.utils import use_cache
from peritype.utils._cache import CACHE


class Plain: ...


def func(a: int) -> int:
    return a


class TestTypeCache:
    def test_same_type_gives_the_same_wrap_while_referenced(self) -> None:
        w = wrap_type(Plain)
        assert wrap_type(Plain) is w
        assert wrap_type(list[Plain]) is wrap_type(list[Plain]) or wrap_type(list[Plain]) == wrap_type(list[Plain])

    def test_equal_spellings_share_a_wrap(self) -> None:
        w = wrap_type(int | None)
        assert wrap_type(None | int) is w

    def test_disabled_cache_builds_fresh_but_equal_wraps(self) -> None:
        use_cache(False)
        a = wrap_type(Plain)
        b = wrap_type(Plain)
        assert a is not b
        assert a == b

    def test_disabling_the_cache_does_not_read_existing_entries(self) -> None:
        w = wrap_type(Plain)
        use_cache(False)
        assert wrap_type(Plain) is not w

    def test_entries_are_weak(self) -> None:
        w = wrap_type(Plain)
        assert Plain in CACHE.twrap_cache
        del w
        gc.collect()
        assert Plain not in CACHE.twrap_cache

    def test_nested_wraps_live_as_long_as_their_parent(self) -> None:
        w = wrap_type(list[Plain])
        gc.collect()
        assert w.generic_params[0] is wrap_type(Plain)

    def test_unhashable_metadata_bypasses_the_cache(self) -> None:
        w = wrap_type(Annotated[int, {"key": 1}])
        assert w.annotations == ({"key": 1},)
        assert w.inner_type is int
        assert w is not wrap_type(Annotated[int, {"key": 1}])
        assert w == wrap_type(Annotated[int, {"key": 1}])
        assert len({w, wrap_type(Annotated[int, {"key": 1}]), wrap_type(Annotated[int, {"key": 2}])}) == 2


class TestFunctionCache:
    def test_same_function_gives_the_same_wrap(self) -> None:
        w = wrap_func(func)
        assert wrap_func(func) is w

    def test_disabled_cache(self) -> None:
        use_cache(False)
        assert wrap_func(func) is not wrap_func(func)

    def test_entries_are_weak(self) -> None:
        w = wrap_func(func)
        assert func in CACHE.fwrap_cache
        del w
        gc.collect()
        assert func not in CACHE.fwrap_cache
