from collections.abc import Iterator
from typing import Any, Self

from peritype import TWrap
from peritype._twrap import Lineage
from peritype.utils import MatchResult


class TypeBag[T = Any]:
    def __init__(self) -> None:
        self._bag = set[TWrap[T]]()
        self._raw_types = dict[type[Any], frozenset[TWrap[T]]]()

    def add(self, twrap: TWrap[T]) -> None:
        self._bag.add(twrap)
        for node in twrap.nodes:
            raw_type = node.inner_type
            self._raw_types[raw_type] = self._raw_types.get(raw_type, frozenset()) | {twrap}

    def remove(self, twrap: TWrap[T]) -> None:
        self._bag.remove(twrap)
        for node in twrap.nodes:
            raw_type = node.inner_type
            if raw_type in self._raw_types:
                remaining = self._raw_types[raw_type] - {twrap}
                if remaining:
                    self._raw_types[raw_type] = remaining
                else:
                    del self._raw_types[raw_type]

    def __contains__(self, twrap: TWrap[T]) -> bool:
        return twrap in self._bag

    def __iter__(self) -> Iterator[TWrap[T]]:
        yield from self._bag

    def __len__(self) -> int:
        return len(self._bag)

    def items(self) -> set[TWrap[T]]:
        return {*self._bag}

    def _candidates(self, twrap: TWrap[T], lineage: Lineage) -> set[TWrap[T]]:
        if lineage != "none" or any(node.inner_type is Any for node in twrap.nodes):
            return self._bag
        candidates = set[TWrap[T]]()
        for node in twrap.nodes:
            candidates |= self._raw_types.get(node.inner_type, frozenset())
        any_type: Any = Any
        candidates |= self._raw_types.get(any_type, frozenset())
        return candidates

    def match_all(
        self, twrap: TWrap[T], *, strict: bool = False, lineage: Lineage = "none"
    ) -> dict[TWrap[T], MatchResult]:
        results: dict[TWrap[T], MatchResult] = {}
        for candidate in self._candidates(twrap, lineage):
            result = twrap.match(candidate, strict=strict, lineage=lineage)
            if result:
                results[candidate] = result
        return results

    def best_matching_or_none(
        self, twrap: TWrap[T], *, strict: bool = False, lineage: Lineage = "none"
    ) -> TWrap[T] | None:
        if twrap in self._bag:
            return twrap
        results = self.match_all(twrap, strict=strict, lineage=lineage)
        if not results:
            return None
        return max(results, key=results.__getitem__)

    def best_matching(self, twrap: TWrap[T], *, strict: bool = False, lineage: Lineage = "none") -> TWrap[T]:
        result = self.best_matching_or_none(twrap, strict=strict, lineage=lineage)
        if result is None:
            raise KeyError(f"No matching type found for {twrap}")
        return result

    def contains_matching(self, twrap: TWrap[T], *, strict: bool = False, lineage: Lineage = "none") -> bool:
        return self.best_matching_or_none(twrap, strict=strict, lineage=lineage) is not None

    def copy(self) -> Self:
        new_bag = type(self)()
        new_bag._bag = self._bag.copy()
        new_bag._raw_types = self._raw_types.copy()
        return new_bag
