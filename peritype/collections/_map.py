from collections.abc import Iterator
from typing import Any, overload

from peritype._twrap import TWrap


class TypeMap[K, V]:
    def __init__(self) -> None:
        self._content: dict[TWrap[K], V] = {}

    def __contains__(self, twrap: TWrap[Any], /) -> bool:
        return twrap in self._content

    def __getitem__(self, twrap: TWrap[K], /) -> V:
        return self._content[twrap]

    def __setitem__(self, twrap: TWrap[K], value: V, /) -> None:
        self._content[twrap] = value

    def __delitem__(self, twrap: TWrap[K], /) -> None:
        del self._content[twrap]

    def __len__(self) -> int:
        return len(self._content)

    def __iter__(self) -> Iterator[tuple[TWrap[K], V]]:
        yield from self._content.items()

    def items(self) -> dict[TWrap[K], V]:
        return {**self._content}

    def keys(self) -> Iterator[TWrap[K]]:
        yield from self._content.keys()

    def values(self) -> Iterator[V]:
        yield from self._content.values()

    @overload
    def get[D](self, twrap: TWrap[K], /, *, default: D) -> V | D: ...
    @overload
    def get(
        self,
        twrap: TWrap[K],
        /,
    ) -> V | None: ...
    def get(
        self,
        twrap: TWrap[K],
        /,
        *,
        default: Any = None,
    ) -> Any:
        return self._content.get(twrap, default)

    def add(self, twrap: TWrap[K], value: V, /) -> None:
        self._content[twrap] = value

    def copy(self) -> "TypeMap[K, V]":
        new_map = TypeMap[K, V]()
        new_map._content = self._content.copy()
        return new_map


class TypeSetMap[K, V](TypeMap[K, set[V]]):
    def push(self, twrap: TWrap[K], value: V, /) -> None:
        if twrap not in self._content:
            self._content[twrap] = set()
        self._content[twrap].add(value)

    def count(self, twrap: TWrap[K], /) -> int:
        if twrap not in self._content:
            return 0
        return len(self._content[twrap])
