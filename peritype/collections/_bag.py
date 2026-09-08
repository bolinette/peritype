from collections.abc import Iterator
from typing import Any

from peritype import TWrap


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

    def first_matching_or_none(self, twrap: TWrap[T]) -> TWrap[T] | None:
        if twrap in self._bag:
            return twrap
        for node in twrap.nodes:
            raw_type = node.inner_type
            if raw_type in self._raw_types:
                for wrap in self._raw_types[raw_type]:
                    if twrap.match(wrap):
                        return wrap
        return None

    def first_matching(self, twrap: TWrap[T]) -> TWrap[T]:
        result = self.first_matching_or_none(twrap)
        if result is None:
            raise KeyError(f"No matching type found for {twrap}")
        return result

    def contains_matching(self, twrap: TWrap[T]) -> bool:
        return self.first_matching_or_none(twrap) is not None

    def get_all_matching(self, twrap: TWrap[T]) -> set[TWrap[T]]:
        if not twrap.contains_any:
            return {twrap} if twrap in self._bag else set()
        result = set[TWrap[T]]()
        for node in twrap.nodes:
            raw_type = node.inner_type
            if raw_type in self._raw_types:
                for wrap in self._raw_types[raw_type]:
                    if twrap.match(wrap):
                        result.add(wrap)
        return result

    def get_all_submatching(self, twrap: TWrap[T]) -> set[TWrap[T]]:
        result = set[TWrap[T]]()
        for twrap_in_bag in self._bag:
            if twrap.match(twrap_in_bag, match_mode="sub"):
                result.add(twrap_in_bag)
        return result

    def copy(self) -> "TypeBag[T]":
        new_bag = TypeBag[T]()
        new_bag._bag = self._bag.copy()
        new_bag._raw_types = self._raw_types.copy()
        return new_bag
