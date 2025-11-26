from collections.abc import Iterator
from typing import Any, Protocol, TypeVar


class TypeVarMapping(Protocol):
    def __getitem__(self, key: TypeVar, /) -> type[Any]: ...

    def __contains__(self, key: TypeVar, /) -> bool: ...

    def __iter__(self, /) -> Iterator[TypeVar]: ...
