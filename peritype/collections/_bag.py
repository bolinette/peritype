from collections.abc import Iterator
from typing import Any

from peritype import TWrap


class TypeBag:
    def __init__(self) -> None:
        self._bag = set[TWrap[Any]]()
        self._raw_types = dict[type[Any], set[TWrap[Any]]]()

    def add(self, twrap: TWrap[Any]) -> None:
        self._bag.add(twrap)
        for node in twrap.nodes:
            raw_type = node.inner_type
            if raw_type not in self._raw_types:
                self._raw_types[raw_type] = set()
            self._raw_types[raw_type].add(twrap)

    def remove(self, twrap: TWrap[Any]) -> None:
        self._bag.remove(twrap)
        for node in twrap.nodes:
            raw_type = node.inner_type
            if raw_type in self._raw_types:
                self._raw_types[raw_type].remove(twrap)
                if not self._raw_types[raw_type]:
                    del self._raw_types[raw_type]

    def __contains__(self, twrap: TWrap[Any]) -> bool:
        return twrap in self._bag

    def __iter__(self) -> Iterator[TWrap[Any]]:
        yield from self._bag

    def __len__(self) -> int:
        return len(self._bag)

    def items(self) -> set[TWrap[Any]]:
        return {*self._bag}

    def first_matching_or_none(self, twrap: TWrap[Any]) -> TWrap[Any] | None:
        if twrap in self._bag:
            return twrap
        for node in twrap.nodes:
            raw_type = node.inner_type
            if raw_type in self._raw_types:
                for wrap in self._raw_types[raw_type]:
                    if twrap.match(wrap):
                        return wrap
        return None

    def first_matching(self, twrap: TWrap[Any]) -> TWrap[Any]:
        result = self.first_matching_or_none(twrap)
        if result is None:
            raise KeyError(f"No matching type found for {twrap}")
        return result

    def contains_matching(self, twrap: TWrap[Any]) -> bool:
        return self.first_matching_or_none(twrap) is not None

    def get_all_matching(self, twrap: TWrap[Any]) -> set[TWrap[Any]]:
        if not twrap.contains_any:
            return {twrap} if twrap in self._bag else set()
        result = set[TWrap[Any]]()
        for node in twrap.nodes:
            raw_type = node.inner_type
            if raw_type in self._raw_types:
                for wrap in self._raw_types[raw_type]:
                    if twrap.match(wrap):
                        result.add(wrap)
        return result

    def get_all_submatching(self, twrap: TWrap[Any]) -> set[TWrap[Any]]:
        result = set[TWrap[Any]]()
        for twrap_in_bag in self._bag:
            if twrap.match(twrap_in_bag, match_mode="sub"):
                result.add(twrap_in_bag)
        return result

    def copy(self) -> "TypeBag":
        new_bag = TypeBag()
        new_bag._bag = self._bag.copy()
        new_bag._raw_types = {k: v.copy() for k, v in self._raw_types.items()}
        return new_bag
