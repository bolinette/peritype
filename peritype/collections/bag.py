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

    def __contains__(self, twrap: TWrap[Any]) -> bool:
        return twrap in self._bag

    def get_matching(self, twrap: TWrap[Any]) -> TWrap[Any] | None:
        if twrap in self._bag:
            return twrap
        for node in twrap.nodes:
            raw_type = node.inner_type
            if raw_type in self._raw_types:
                for wrap in self._raw_types[raw_type]:
                    if twrap.match(wrap):
                        return wrap
        return None

    def contains_matching(self, twrap: TWrap[Any]) -> bool:
        return self.get_matching(twrap) is not None

    def get_all(self, twrap: TWrap[Any]) -> set[TWrap[Any]]:
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

    def copy(self) -> "TypeBag":
        new_bag = TypeBag()
        new_bag._bag = self._bag.copy()
        new_bag._raw_types = {k: v.copy() for k, v in self._raw_types.items()}
        return new_bag
