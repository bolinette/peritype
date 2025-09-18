from collections.abc import Callable, Iterator
from functools import cached_property
from types import NoneType
from typing import Any, ForwardRef, Literal, TypeVar, cast, override

import peritype


class TWrapMeta:
    def __init__(
        self,
        *,
        annotated: tuple[Any],
        required: bool,
        total: bool,
    ) -> None:
        self.annotated = annotated
        self.required = required
        self.total = total

    @cached_property
    def _hash(self) -> int:
        return hash((self.annotated, self.required, self.total))

    @override
    def __hash__(self) -> int:
        return self._hash


class TypeVarLookup:
    def __init__(self, origins: dict[TypeVar, Any], twraps: dict[TypeVar, "TWrap[Any]"]) -> NoneType:
        self.origin_mapping = origins
        self.twrap_mapping = twraps

    def __getitem__(self, key: TypeVar, /) -> Any:
        if key not in self.twrap_mapping:
            raise KeyError(key)
        return self.origin_mapping[key]

    def __contains__(self, key: TypeVar, /) -> bool:
        return key in self.origin_mapping

    def __iter__(self, /) -> Iterator[TypeVar]:
        yield from self.origin_mapping

    def __or__(self, other: "TypeVarLookup") -> "TypeVarLookup":
        new_origins = self.origin_mapping | other.origin_mapping
        new_twraps = self.twrap_mapping | other.twrap_mapping
        return TypeVarLookup(new_origins, new_twraps)

    def origin_items(self, /) -> Iterator[tuple[TypeVar, Any]]:
        yield from self.origin_mapping.items()

    def twrap_items(self, /) -> Iterator[tuple[TypeVar, "TWrap[Any]"]]:
        yield from self.twrap_mapping.items()

    def get_origin[DefT](self, key: TypeVar, /, default: DefT | None = None) -> Any | DefT | None:
        if key not in self.twrap_mapping:
            return default
        return self.origin_mapping[key]

    def get_twrap[DefT](self, key: TypeVar, /, default: DefT | None = None) -> Any | DefT | None:
        if key not in self.twrap_mapping:
            return default
        return self.twrap_mapping[key]


class TypeNode[T]:
    def __init__(
        self,
        origin: Any,
        nodes: "tuple[TWrap[Any], ...]",
        cls: type[T],
        vars: tuple[Any, ...],
    ) -> None:
        self.origin = origin
        self.nodes = nodes
        self.cls = cls
        self.vars = vars

    @staticmethod
    def _format_type(v: Any) -> str:
        if isinstance(v, type):
            return v.__qualname__
        if isinstance(v, TypeVar):
            return f"~{v.__name__}"
        if v is Ellipsis:
            return "..."
        if v is Literal:
            return v.__name__
        if isinstance(v, ForwardRef):
            return f"'{v.__forward_arg__}'"
        return str(v)

    @cached_property
    def _str(self) -> str:
        if not self.vars:
            return self._format_type(self.cls)
        return f"{self._format_type(self.cls)}[{', '.join(map(self._format_type, self.vars))}]"

    @override
    def __str__(self) -> str:
        return self._str

    @override
    def __repr__(self) -> str:
        return f"<TypeNode {self._str}>"

    @cached_property
    def _hash(self) -> int:
        return hash((self.cls, self.nodes))

    @override
    def __hash__(self) -> int:
        return self._hash

    def __getitem__(self, index: int) -> "TWrap[Any]":
        return self.nodes[index]

    @cached_property
    def base_name(self) -> str:
        return self._format_type(self.cls)

    @cached_property
    def contains_any(self) -> bool:
        if self.cls is Any or self.cls is Ellipsis:  # pyright: ignore[reportUnnecessaryComparison]
            return True
        if isinstance(self.cls, tuple) and Any in self.cls:
            return True
        for node in self.nodes:
            if node.contains_any:
                return True
        return False

    @cached_property
    def bases(self) -> tuple["TWrap[Any]", ...]:
        bases: list[TWrap[Any]] = []
        if hasattr(self.cls, "__orig_bases__"):
            origin_bases: tuple[type[Any], ...] = getattr(self.cls, "__orig_bases__", ())
            for base in origin_bases:
                bases.append(peritype.wrap_type(base, lookup=self.type_var_lookup))
        elif hasattr(self.cls, "__bases__"):
            cls_bases = getattr(self.cls, "__bases__", ())
            for base in cls_bases:
                bases.append(peritype.wrap_type(base, lookup=self.type_var_lookup))
        return tuple(bases)

    @cached_property
    def type_var_lookup(self) -> TypeVarLookup:
        parameters = getattr(self.cls, "__type_params__", None) or getattr(self.cls, "__parameters__", None)
        origin_lookup = dict(zip(parameters, self.vars, strict=True)) if parameters else {}
        twrap_lookup = dict(zip(parameters, self.nodes, strict=True)) if parameters else {}
        lookup = TypeVarLookup(origin_lookup, twrap_lookup)
        base_lookup = TypeVarLookup({}, {})
        if hasattr(self.cls, "__orig_bases__"):
            origin_bases: tuple[type[Any], ...] = getattr(self.cls, "__orig_bases__", ())
            for base in origin_bases:
                base_wrap = peritype.wrap_type(base, lookup=lookup)
                base_lookup |= base_wrap.type_var_lookup
        return base_lookup | lookup


class TWrap[T]:
    def __init__(
        self,
        *,
        origin: Any,
        nodes: tuple[TypeNode[Any], ...],
        meta: TWrapMeta,
    ) -> None:
        self._origin = origin
        self._nodes = nodes
        self._meta = meta

    @cached_property
    def _hash(self) -> int:
        return hash(((*sorted(self._nodes, key=str),), self._meta))

    @override
    def __hash__(self) -> int:
        return self._hash

    @cached_property
    def _str(self) -> str:
        return " | ".join(str(n) for n in self._nodes)

    @override
    def __str__(self) -> str:
        return self._str

    @cached_property
    def _repr(self) -> str:
        return f"<Type {self}>"

    @override
    def __repr__(self) -> str:
        return self._repr

    def __visit__(self, *, for_nodes: Callable[[TypeNode[Any]], None] | None = None) -> None:
        if for_nodes:
            for node in self._nodes:
                for_nodes(node)

    def __getitem__(self, index: int) -> TypeNode[Any]:
        return self.nodes[index]

    @property
    def origin(self) -> type[T]:
        return self._origin

    @property
    def required(self) -> bool:
        return self._meta.required

    @property
    def total(self) -> bool:
        return self._meta.total

    @property
    def nodes(self) -> tuple["TypeNode[Any]", ...]:
        return self._nodes

    @cached_property
    def type_var_lookup(self) -> TypeVarLookup:
        lookup = TypeVarLookup({}, {})
        for node in self._nodes:
            lookup |= node.type_var_lookup
        return lookup

    @cached_property
    def contains_any(self) -> bool:
        return any(node.contains_any for node in self._nodes)

    @cached_property
    def is_union(self) -> bool:
        return len([n for n in self._nodes if n.cls is not NoneType]) > 1

    @cached_property
    def is_nullable(self) -> bool:
        return any(n.cls is NoneType for n in self._nodes)

    def match(self, other: Any) -> bool:
        other_wrap: TWrap[Any]
        if isinstance(other, TWrap):
            other_wrap = cast(TWrap[Any], other)
        else:
            other_wrap = peritype.wrap_type(other)

        for a in self._nodes:
            for b in other_wrap._nodes:
                if self._nodes_intersect(a, b):
                    return True
        return False

    @staticmethod
    def _nodes_intersect(a: "TypeNode[Any]", b: "TypeNode[Any]") -> bool:
        if a.origin is Any or b.origin is Any:
            return True
        if a.origin is Ellipsis or b.origin is Ellipsis:
            return True

        if a.cls is not b.cls:
            return False

        if not a.nodes and not b.nodes:
            return True

        if len(a.nodes) != len(b.nodes):
            return False

        for i in range(len(a.nodes)):
            if not a.nodes[i].match(b.nodes[i]):
                return False
        return True
