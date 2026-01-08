import inspect
from collections.abc import Iterator
from functools import cached_property
from types import NoneType
from typing import TYPE_CHECKING, Any, ForwardRef, Literal, TypeVar, cast, get_type_hints, override

import peritype
from peritype.errors import PeritypeError

if TYPE_CHECKING:
    from peritype.fwrap import BoundFWrap, FWrap


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
        generic_params: "tuple[TWrap[Any], ...]",
        inner_type: type[T],
        origin_params: tuple[Any, ...],
    ) -> None:
        self._origin = origin
        self._generic_params = generic_params
        self._inner_type = inner_type
        self._origin_params = origin_params

    @property
    def origin(self) -> Any:
        return self._origin

    @property
    def generic_params(self) -> "tuple[TWrap[Any], ...]":
        return self._generic_params

    @property
    def inner_type(self) -> type[T]:
        return self._inner_type

    @property
    def origin_params(self) -> tuple[Any, ...]:
        return self._origin_params

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
        if not self._origin_params:
            return self._format_type(self._inner_type)
        return f"{self._format_type(self._inner_type)}[{', '.join(map(self._format_type, self._origin_params))}]"

    @override
    def __str__(self) -> str:
        return self._str

    @override
    def __repr__(self) -> str:
        return f"<TypeNode {self._str}>"

    @cached_property
    def _hash(self) -> int:
        return hash((self._inner_type, self._generic_params))

    @override
    def __hash__(self) -> int:
        return self._hash

    @override
    def __eq__(self, value: object) -> bool:
        if not isinstance(value, TypeNode):
            return False
        return hash(self) == hash(value)  # pyright: ignore[reportUnknownArgumentType]

    def __getitem__(self, index: int) -> "TWrap[Any]":
        return self._generic_params[index]

    @cached_property
    def base_name(self) -> str:
        return self._format_type(self._inner_type)

    @cached_property
    def contains_any(self) -> bool:
        if self._inner_type is Any or self._inner_type is Ellipsis:  # pyright: ignore[reportUnnecessaryComparison]
            return True
        if isinstance(self._inner_type, tuple) and Any in self._inner_type:
            return True
        for node in self._generic_params:
            if node.contains_any:
                return True
        return False

    @cached_property
    def bases(self) -> tuple["TWrap[Any]", ...]:
        bases: list[TWrap[Any]] = []
        if hasattr(self._inner_type, "__orig_bases__"):
            origin_bases: tuple[type[Any], ...] = getattr(self._inner_type, "__orig_bases__", ())
            for base in origin_bases:
                bases.append(peritype.wrap_type(base, lookup=self.type_var_lookup))
        elif hasattr(self._inner_type, "__bases__"):
            cls_bases = getattr(self._inner_type, "__bases__", ())
            for base in cls_bases:
                bases.append(peritype.wrap_type(base, lookup=self.type_var_lookup))
        return (*bases,)

    @cached_property
    def type_var_lookup(self) -> TypeVarLookup:
        parameters = getattr(self._inner_type, "__type_params__", None) or getattr(
            self._inner_type, "__parameters__", None
        )
        origin_lookup = dict(zip(parameters, self._origin_params, strict=True)) if parameters else {}
        twrap_lookup = dict(zip(parameters, self._generic_params, strict=True)) if parameters else {}
        lookup = TypeVarLookup(origin_lookup, twrap_lookup)
        base_lookup = TypeVarLookup({}, {})
        if hasattr(self._inner_type, "__orig_bases__"):
            origin_bases: tuple[type[Any], ...] = getattr(self._inner_type, "__orig_bases__", ())
            for base in origin_bases:
                base_wrap = peritype.wrap_type(base, lookup=lookup)
                base_lookup |= base_wrap.type_var_lookup
        return base_lookup | lookup

    @cached_property
    def attribute_hints(self) -> "dict[str, TWrap[Any]]":
        if self._inner_type is NoneType:
            return {}
        return self._get_recursive_attribute_hints(self._inner_type)

    def _get_recursive_attribute_hints(self, cls: type[Any]) -> "dict[str, TWrap[Any]]":
        attr_hints: dict[str, TWrap[Any]] = {}
        try:
            for base in cls.__bases__:
                attr_hints |= self._get_recursive_attribute_hints(base)
            raw_ints: dict[str, type[Any] | TypeVar] = get_type_hints(cls, include_extras=True)
            for attr_name, hint in raw_ints.items():
                if isinstance(hint, TypeVar):
                    if hint in self.type_var_lookup:
                        attr_hints[attr_name] = peritype.wrap_type(self.type_var_lookup[hint])
                    else:
                        raise PeritypeError(f"TypeVar ~{hint.__name__} could not be found in lookup", cls=cls)
                else:
                    attr_hints[attr_name] = peritype.wrap_type(hint, lookup=self.type_var_lookup)
        except (AttributeError, TypeError, NameError):
            return attr_hints
        return attr_hints

    @cached_property
    def init(self) -> "FWrap[..., Any]":
        if not hasattr(self._inner_type, "__init__"):
            raise TypeError("No __init__ method found in type nodes")
        init_func = self._inner_type.__init__
        return peritype.wrap_func(init_func)

    @cached_property
    def signature(self) -> inspect.Signature:
        return self.init.signature

    @cached_property
    def parameters(self) -> dict[str, inspect.Parameter]:
        return {**self.signature.parameters}

    def instantiate(self, /, *args: Any, **kwargs: Any) -> T:
        return self._inner_type(*args, **kwargs)

    def get_method(self, method_name: str) -> "FWrap[..., Any]":
        if not hasattr(self._inner_type, method_name):
            raise AttributeError(f"Method '{method_name}' not found")
        method_func = getattr(self._inner_type, method_name)
        return peritype.wrap_func(method_func)

    def match(self, other: "TWrap[Any]") -> bool:
        for other_node in other.nodes:
            if self._nodes_intersect(other_node):
                return True
        return False

    def _nodes_intersect(self, b: "TypeNode[Any]") -> bool:
        if self._origin is Any or b._origin is Any:
            return True
        if self._origin is Ellipsis or b._origin is Ellipsis:
            return True

        if self._inner_type is not b._inner_type:
            return False

        if not self._generic_params and not b._generic_params:
            return True

        if len(self._generic_params) != len(b._generic_params):
            return False

        for i in range(len(self._generic_params)):
            if not self._generic_params[i].match(b._generic_params[i]):
                return False
        return True


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
        self._method_cache: dict[str, BoundFWrap[..., Any]] = {}

    @cached_property
    def _hash(self) -> int:
        return hash(((*sorted(self._nodes, key=str),), self._meta))

    @override
    def __hash__(self) -> int:
        return self._hash

    @override
    def __eq__(self, value: object) -> bool:
        if not isinstance(value, TWrap):
            return False
        return hash(self) == hash(value)  # pyright: ignore[reportUnknownArgumentType]

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

    @cached_property
    def annotations(self) -> tuple[Any, ...]:
        return self._meta.annotated

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
    def union(self) -> bool:
        return len([n for n in self._nodes if n.inner_type is not NoneType]) > 1

    @cached_property
    def nullable(self) -> bool:
        return any(n.inner_type is NoneType for n in self._nodes)

    @cached_property
    def attribute_hints(self) -> "dict[str, TWrap[Any]]":
        if self.union:
            raise TypeError("Cannot get attributes of union types")
        return self._nodes[0].attribute_hints

    @cached_property
    def init(self) -> "BoundFWrap[..., Any]":
        if self.union:
            raise TypeError("Cannot get __init__ of union types")
        return self._nodes[0].init.bind(self)

    @cached_property
    def signature(self) -> inspect.Signature:
        if self.union:
            raise TypeError("Cannot get signature of union types")
        return inspect.signature(self._nodes[0].inner_type)

    @cached_property
    def parameters(self) -> dict[str, inspect.Parameter]:
        return {**self.signature.parameters}

    @cached_property
    def inner_type(self) -> Any:
        if self.union:
            raise TypeError("Cannot get inner type of union types")
        return self._nodes[0].inner_type

    @cached_property
    def generic_params(self) -> "tuple[TWrap[Any], ...]":
        if self.union:
            raise TypeError("Cannot get generic params of union types")
        return self._nodes[0].generic_params

    def instantiate(self, /, *args: Any, **kwargs: Any) -> T:
        if self.union:
            raise TypeError("Cannot instantiate union types")
        return self._nodes[0].instantiate(*args, **kwargs)

    def get_method(self, method_name: str) -> "BoundFWrap[..., Any]":
        if self.union:
            raise TypeError("Cannot get methods of union types")
        if method_name in self._method_cache:
            return self._method_cache[method_name]
        return self._nodes[0].get_method(method_name).bind(self)

    def match(self, other: Any) -> bool:
        other_wrap: TWrap[Any]
        if isinstance(other, TWrap):
            other_wrap = cast(TWrap[Any], other)
        else:
            other_wrap = peritype.wrap_type(other)

        for a in self._nodes:
            if a.match(other_wrap):
                return True
        return False
