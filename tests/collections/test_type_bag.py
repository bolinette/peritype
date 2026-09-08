"""``TypeBag``: an unordered set of wraps with match-based lookup."""

from typing import Any

import pytest

from peritype import TWrap, wrap_type
from peritype.collections import TypeBag


class Root: ...


class Mid(Root): ...


class Other: ...


@pytest.fixture
def bag() -> TypeBag[Any]:
    bag = TypeBag[Any]()
    bag.add(wrap_type(list[int]))
    bag.add(wrap_type(list[str]))
    bag.add(wrap_type(dict[str, int]))
    return bag


class TestSetBehaviour:
    def test_add_contains_len(self, bag: TypeBag[Any]) -> None:
        assert len(bag) == 3
        assert wrap_type(list[int]) in bag
        assert wrap_type(set[int]) not in bag

    def test_adding_twice_is_idempotent(self, bag: TypeBag[Any]) -> None:
        bag.add(wrap_type(list[int]))
        assert len(bag) == 3

    def test_iteration_and_items(self, bag: TypeBag[Any]) -> None:
        expected = {wrap_type(list[int]), wrap_type(list[str]), wrap_type(dict[str, int])}
        assert set(bag) == expected
        assert bag.items() == expected
        assert bag.items() is not bag.items()

    def test_remove(self, bag: TypeBag[Any]) -> None:
        bag.remove(wrap_type(list[int]))
        assert wrap_type(list[int]) not in bag
        assert len(bag) == 2
        assert bag.best_matching_or_none(wrap_type(list[int])) is None

    def test_remove_missing_raises(self, bag: TypeBag[Any]) -> None:
        with pytest.raises(KeyError):
            bag.remove(wrap_type(set[int]))

    def test_copy_is_independent(self, bag: TypeBag[Any]) -> None:
        copy = bag.copy()
        copy.add(wrap_type(set[int]))
        copy.remove(wrap_type(list[int]))
        assert wrap_type(set[int]) not in bag
        assert wrap_type(list[int]) in bag
        assert wrap_type(set[int]) in copy
        assert copy.contains_matching(wrap_type(set[int]))

    def test_nullable_entries_can_be_removed_independently(self) -> None:
        bag = TypeBag[Any]()
        bag.add(wrap_type(int | None))
        bag.add(wrap_type(str | None))
        bag.remove(wrap_type(int | None))
        assert bag.contains_matching(wrap_type(None))
        assert bag.best_matching(wrap_type(str | None)) == wrap_type(str | None)
        bag.remove(wrap_type(str | None))
        assert not bag.contains_matching(wrap_type(None))


class TestMatching:
    def test_exact_lookup(self, bag: TypeBag[Any]) -> None:
        assert bag.best_matching(wrap_type(list[int])) == wrap_type(list[int])
        assert bag.contains_matching(wrap_type(dict[str, int]))

    def test_missing_lookup(self, bag: TypeBag[Any]) -> None:
        assert bag.best_matching_or_none(wrap_type(set[int])) is None
        assert not bag.contains_matching(wrap_type(set[int]))
        with pytest.raises(KeyError):
            bag.best_matching(wrap_type(set[int]))

    def test_query_with_any_matches_a_stored_type(self, bag: TypeBag[Any]) -> None:
        found = bag.best_matching(wrap_type(dict[str, Any]))
        assert found == wrap_type(dict[str, int])

    def test_stored_any_matches_a_concrete_query(self) -> None:
        bag = TypeBag[Any]()
        bag.add(wrap_type(list[Any]))
        assert bag.best_matching(wrap_type(list[int])) == wrap_type(list[Any])

    def test_union_query_matches_any_member(self, bag: TypeBag[Any]) -> None:
        assert bag.best_matching(wrap_type(set[int] | dict[str, int])) == wrap_type(dict[str, int])


class TestMatchAll:
    def test_returns_a_result_per_matching_entry(self) -> None:
        bag = TypeBag[Any]()
        bag.add(wrap_type(list[int]))
        bag.add(wrap_type(list[Any]))
        bag.add(wrap_type(dict[str, int]))
        results = bag.match_all(wrap_type(list[int]))
        assert set(results) == {wrap_type(list[int]), wrap_type(list[Any])}
        assert results[wrap_type(list[int])].is_exact
        assert results[wrap_type(list[Any])].is_catchall

    def test_empty_when_nothing_matches(self, bag: TypeBag[Any]) -> None:
        assert bag.match_all(wrap_type(set[int])) == {}
        assert TypeBag[Any]().match_all(wrap_type(int)) == {}

    def test_strict_drops_catchalls(self) -> None:
        bag = TypeBag[Any]()
        bag.add(wrap_type(list[int]))
        bag.add(wrap_type(list[Any]))
        assert set(bag.match_all(wrap_type(list[int]), strict=True)) == {wrap_type(list[int])}

    def test_lineage_reaches_stored_parents(self) -> None:
        bag = TypeBag[Any]()
        bag.add(wrap_type(Root))
        bag.add(wrap_type(Other))
        results = bag.match_all(wrap_type(Mid), lineage="super")
        assert set(results) == {wrap_type(Root)}
        assert results[wrap_type(Root)].is_lineage
        assert bag.match_all(wrap_type(Mid)) == {}

    def test_any_query_sees_every_entry(self, bag: TypeBag[Any]) -> None:
        results = bag.match_all(wrap_type(Any))
        assert set(results) == bag.items()
        assert all(result.is_catchall for result in results.values())

    def test_stored_any_is_always_a_candidate(self) -> None:
        bag = TypeBag[Any]()
        bag.add(wrap_type(Any))
        bag.add(wrap_type(str))
        results = bag.match_all(wrap_type(int))
        assert set(results) == {wrap_type(Any)}
        assert results[wrap_type(Any)].is_catchall


class TestBestMatch:
    def test_strongest_result_wins(self) -> None:
        bag = TypeBag[Any]()
        bag.add(wrap_type(list[Any]))
        bag.add(wrap_type(list[int | str]))
        assert bag.best_matching(wrap_type(list[int])) == wrap_type(list[int | str])

    def test_exact_beats_lineage(self) -> None:
        bag = TypeBag[Any]()
        bag.add(wrap_type(Root))
        bag.add(wrap_type(Mid | None))
        assert bag.best_matching(wrap_type(Mid), lineage="super") == wrap_type(Mid | None)

    def test_lineage_only_when_asked(self) -> None:
        bag = TypeBag[Any]()
        bag.add(wrap_type(Root))
        assert bag.best_matching_or_none(wrap_type(Mid)) is None
        assert bag.best_matching_or_none(wrap_type(Mid), lineage="super") == wrap_type(Root)
        assert bag.contains_matching(wrap_type(Mid), lineage="super")
        assert not bag.contains_matching(wrap_type(Mid))

    def test_strict_lookup(self) -> None:
        bag = TypeBag[Any]()
        bag.add(wrap_type(list[Any]))
        assert bag.best_matching_or_none(wrap_type(list[int])) == wrap_type(list[Any])
        assert bag.best_matching_or_none(wrap_type(list[int]), strict=True) is None
        with pytest.raises(KeyError):
            bag.best_matching(wrap_type(list[int]), strict=True)


class TestTyping:
    def test_bag_is_generic_over_the_wrapped_type(self) -> None:
        bag = TypeBag[Root]()
        root: TWrap[Root] = wrap_type(Root)
        bag.add(root)
        assert bag.best_matching(root) is root
