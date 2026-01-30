from typing import Any, ForwardRef, Generic, get_origin

from peritype._wrap import TWrap
from peritype.collections import TypeSetMap


class TypeSuperTree:
    def __init__(self) -> None:
        self._content = TypeSetMap[Any, TWrap[Any]]()

    def add(self, twrap: TWrap[Any]) -> None:
        bases = set[TWrap[Any]]()
        self._recurse_all_bases(twrap, bases)
        for base in bases:
            self._add_type(base, twrap)

    def __contains__(self, twrap: TWrap[Any]) -> bool:
        return twrap in self._content

    def __getitem__(self, twrap: TWrap[Any]) -> set[TWrap[Any]]:
        return self._content[twrap]

    def __delitem__(self, twrap: TWrap[Any]) -> None:
        del self._content[twrap]

    def _add_type(self, base: TWrap[Any], derived: TWrap[Any]) -> None:
        self._content.push(base, derived)

    @staticmethod
    def _recurse_all_bases(
        twrap: TWrap[Any],
        seen: set[TWrap[Any]],
    ) -> None:
        if twrap in seen:
            return
        seen.add(twrap)
        for node in twrap.nodes:
            for base in node.bases:
                origin = get_origin(base.origin)
                if (origin or base.origin) in (object, Generic, ForwardRef):
                    continue
                TypeSuperTree._recurse_all_bases(base, seen)

    def copy(self) -> "TypeSuperTree":
        new_tree = TypeSuperTree()
        new_tree._content = self._content.copy()
        return new_tree
