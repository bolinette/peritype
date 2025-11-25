from typing import Any, Literal, overload

from peritype.twrap import TWrap


class TypeMap:
    def __init__(self) -> None:
        self._content: dict[TWrap[Any], set[Any]] = {}

    def __contains__(self, twrap: TWrap[Any], /) -> bool:
        return twrap in self._content

    def __getitem__(self, twrap: TWrap[Any], /) -> set[Any]:
        return self._content[twrap]

    def __setitem__(self, twrap: TWrap[Any], /, value: set[Any]) -> None:
        self._content[twrap] = value

    def __delitem__(self, twrap: TWrap[Any], /) -> None:
        del self._content[twrap]

    @overload
    def get[T](
        self,
        twrap: TWrap[Any],
        /,
        *,
        not_none: Literal[False] = False,
        hint: type[T] | TWrap[T],
    ) -> set[T] | None: ...
    @overload
    def get[T](
        self,
        twrap: TWrap[Any],
        /,
        *,
        not_none: Literal[True],
        hint: type[T] | TWrap[T],
    ) -> set[T]: ...
    @overload
    def get(
        self,
        twrap: TWrap[Any],
        /,
        *,
        not_none: Literal[False] = False,
        hint: type[Any] | TWrap[Any] | None = None,
    ) -> set[Any] | None: ...
    @overload
    def get(
        self,
        twrap: TWrap[Any],
        /,
        *,
        not_none: Literal[True],
        hint: type[Any] | TWrap[Any] | None = None,
    ) -> set[Any] | None: ...
    def get(
        self,
        twrap: TWrap[Any],
        /,
        *,
        not_none: bool = False,
        hint: type[Any] | TWrap[Any] | None = None,
    ) -> set[Any] | None:
        if not_none and twrap not in self._content:
            return set()
        return self._content.get(twrap)

    def push(self, twrap: TWrap[Any], value: Any) -> None:
        if twrap not in self._content:
            self._content[twrap] = set()
        self._content[twrap].add(value)
