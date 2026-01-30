import inspect
from collections.abc import Iterator
from functools import cached_property
from types import NoneType
from typing import (
    TYPE_CHECKING,
    Any,
    ForwardRef,
    Generic,
    Literal,
    TypeGuard,
    TypeVar,
    Union,  # pyright: ignore[reportDeprecated]
    cast,
    get_args,
    get_origin,
    get_type_hints,
    override,
)

import peritype
from peritype.errors import IncompatibleTypesError, UnresolvedTypeVarError
from peritype.utils import WithOriginClass
from peritype.utils._cache import CACHE

if TYPE_CHECKING:
    from peritype._fwrap import BoundFWrap, FWrap

type MatchMode = Literal["exact", "super", "sub", "any"]


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
    def __init__(self, origins: dict[TypeVar, Any], twraps: dict[TypeVar, "TWrap[Any]"]) -> None:
        origin_keys = set(origins.keys())
        twrap_keys = set(twraps.keys())
        if origin_keys != twrap_keys:
            raise ValueError("Origins and TWraps must have the same TypeVar keys")
        self._type_vars = origin_keys
        self._origin_mapping = origins
        self._twrap_mapping = twraps
        self._eq_outward: dict[TypeVar, set[TypeVar]] = {}
        self._eq_inward: dict[TypeVar, TypeVar] = {}

    def __getitem__(self, key: TypeVar, /) -> Any:
        if key in self._origin_mapping:
            return self._origin_mapping[key]
        raise KeyError(key)

    def get_twrap(self, key: TypeVar, /, equivalent: "TypeVarLookup | None" = None) -> "TWrap[Any]":
        if key in self._twrap_mapping:
            return self._twrap_mapping[key]
        if equivalent is not None and equivalent._has_equivalent(key):
            return equivalent._get_by_equivalent(self._twrap_mapping, key)
        raise KeyError(key)

    def __contains__(self, key: TypeVar, /) -> bool:
        return key in self._type_vars

    def __iter__(self, /) -> Iterator[TypeVar]:
        yield from self._origin_mapping

    def __len__(self, /) -> int:
        return len(self._origin_mapping)

    def _merge(self, other: "TypeVarLookup", *, base_mode: bool) -> "TypeVarLookup":
        new_origins = self._origin_mapping | other._origin_mapping
        new_twraps = self._twrap_mapping | other._twrap_mapping
        lookup = TypeVarLookup(new_origins, new_twraps)
        lookup._eq_outward = {**self._eq_outward}
        for k, v in other._eq_outward.items():
            if k in lookup._eq_outward:
                lookup._eq_outward[k].update(v)
            else:
                lookup._eq_outward[k] = v
        lookup._eq_inward = {**self._eq_inward, **other._eq_inward}
        if base_mode:
            for in_tv, out_tvs in ((k, set(v)) for k, v in lookup._eq_outward.items()):
                for out_tv in out_tvs:
                    lookup._eq_outward[in_tv].update(lookup._eq_outward.get(out_tv, set()))
        return lookup

    def __or__(self, other: "TypeVarLookup", /) -> "TypeVarLookup":
        return self._merge(other, base_mode=False)

    def merge_base(self, other: "TypeVarLookup") -> "TypeVarLookup":
        return self._merge(other, base_mode=True)

    def replace_with(self, type_vars: tuple[TypeVar, ...]) -> "TypeVarLookup":
        origin_mapping: dict[TypeVar, Any] = {}
        twrap_mapping: dict[TypeVar, TWrap[Any]] = {}
        for old_var, new_var in zip(self._origin_mapping.keys(), type_vars, strict=True):
            origin_mapping[new_var] = self._origin_mapping[old_var]
            twrap_mapping[new_var] = self._twrap_mapping[old_var]
        return TypeVarLookup(origin_mapping, twrap_mapping)

    def set_equivalents(self, base: type[Any]) -> None:
        base_origin = get_origin(base)
        if base_origin is None:
            return
        args = get_args(base)
        base_params = (
            getattr(base_origin, "__type_params__", None) or getattr(base_origin, "__parameters__", None) or ()
        )
        for param, arg in zip(base_params, args, strict=True):
            if isinstance(arg, TypeVar) and arg in self._type_vars:
                if arg not in self._eq_outward:
                    self._eq_outward[arg] = set()
                self._eq_outward[arg].add(param)
                self._eq_inward[param] = arg

    def _has_equivalent(self, type_var: TypeVar) -> bool:
        return type_var in self._eq_inward or type_var in self._eq_outward

    def _get_by_equivalent(self, mapping: dict[TypeVar, "TWrap[Any]"], type_var: TypeVar) -> "TWrap[Any]":
        if type_var in self._eq_inward:
            return mapping[self._eq_inward[type_var]]
        if type_var in self._eq_outward:
            key = next((t for t in self._eq_outward[type_var] if t in mapping), None)
            if key is not None:
                return mapping[key]
            return peritype.wrap_type(Any)
        raise KeyError(type_var)


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
        self._bases: tuple[TWrap[Any], ...] | None = None
        self._type_var_lookup: TypeVarLookup | None = None

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
    def type_params(self) -> "tuple[TypeVar, ...]":
        return (
            getattr(self._inner_type, "__type_params__", None)
            or getattr(self._inner_type, "__parameters__", None)
            or ()
        )

    def _get_bases_and_type_var_lookup(self) -> "tuple[tuple['TWrap[Any]', ...], TypeVarLookup]":
        bases: list[TWrap[Any]] = []
        type_params = self.type_params
        origin_lookup = dict(zip(type_params, self._origin_params, strict=True)) if type_params else {}
        twrap_lookup = dict(zip(type_params, self._generic_params, strict=True)) if type_params else {}
        lookup = TypeVarLookup(origin_lookup, twrap_lookup)
        origin_bases: tuple[type[Any], ...] = getattr(
            self._inner_type, "__orig_bases__", getattr(self._inner_type, "__bases__", ())
        )
        for base in origin_bases:
            if (base_origin := get_origin(base)) and base_origin is Generic:
                continue
            lookup.set_equivalents(base)
            base_wrap = peritype.wrap_type(base, lookup=lookup)
            bases.append(base_wrap)
            lookup = lookup.merge_base(base_wrap.type_var_lookup)
        return (*bases,), lookup

    @property
    def bases(self) -> tuple["TWrap[Any]", ...]:
        if self._bases is None:
            self._bases, self._type_var_lookup = self._get_bases_and_type_var_lookup()
        return self._bases

    @property
    def type_var_lookup(self) -> TypeVarLookup:
        if self._type_var_lookup is None:
            self._bases, self._type_var_lookup = self._get_bases_and_type_var_lookup()
        return self._type_var_lookup

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
                        raise UnresolvedTypeVarError(hint.__name__, cls=cls)
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
        return self._origin(*args, **kwargs)

    def get_method(self, method_name: str) -> "FWrap[..., Any]":
        if not hasattr(self._inner_type, method_name):
            raise AttributeError(f"Method '{method_name}' not found")
        method_func = getattr(self._inner_type, method_name)
        return peritype.wrap_func(method_func)

    def match(self, other: "TWrap[Any]", *, match_mode: MatchMode = "exact") -> bool:
        for other_node in other.nodes:
            if self._nodes_intersect(other_node, match_mode=match_mode):
                return True
        return False

    def _match_super(self, b: "TypeNode[Any]") -> bool:
        for base in self.bases:
            if b.match(base):
                return True
        return False

    def _match_sub(self, b: "TypeNode[Any]") -> bool:
        for base in b.bases:
            if self.match(base):
                return True
        return False

    def _nodes_intersect(self, b: "TypeNode[Any]", *, match_mode: MatchMode = "exact") -> bool:
        if self._origin is Any or b._origin is Any:
            return True
        if self._origin is Ellipsis or b._origin is Ellipsis:
            return True

        if self._inner_type is not b._inner_type:
            match match_mode:
                case "exact":
                    return False
                case "super":
                    return self._match_super(b)
                case "sub":
                    return self._match_sub(b)
                case "any":
                    return self._match_super(b) or self._match_sub(b)

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

    def match(self, other: Any, *, match_mode: MatchMode = "exact") -> bool:
        other_wrap: TWrap[Any]
        if isinstance(other, TWrap):
            other_wrap = cast(TWrap[Any], other)
        else:
            other_wrap = peritype.wrap_type(other)

        for a in self._nodes:
            if a.match(other_wrap, match_mode=match_mode):
                return True
        return False

    def is_type_of(self, value: Any) -> TypeGuard[T]:
        if WithOriginClass.match(value):
            return self.match(peritype.wrap_type(value.__orig_class__), match_mode="sub")
        value_type: type[Any] = cast(type[Any], type(value))
        return self.match(peritype.wrap_type(value_type), match_mode="sub")

    def specialize_with(self, twrap: "TWrap[Any]") -> "TWrap[Any]":
        try:
            new_nodes: list[TypeNode[Any]] = []
            for node in self._nodes:
                new_params: list[TWrap[Any]] = []
                for type_param in node.type_params:
                    replacement = twrap.type_var_lookup.get_twrap(type_param, equivalent=self.type_var_lookup)
                    new_params.append(replacement)
                new_origin_params = tuple(p.inner_type for p in new_params)
                new_origin = cast(Any, node.inner_type)[*new_origin_params]
                new_nodes.append(TypeNode(new_origin, tuple(new_params), node.inner_type, new_origin_params))
            new_origin = cast(Any, Union[*(n.origin for n in new_nodes)])  # pyright: ignore[reportDeprecated]
            new_twrap = cast(
                TWrap[Any],
                TWrap(
                    origin=new_origin,
                    nodes=tuple(new_nodes),
                    meta=self._meta,
                ),
            )
            CACHE.set_twrap(new_twrap._origin, new_twrap)
            return new_twrap
        except KeyError as e:
            raise IncompatibleTypesError(self._origin, twrap._origin) from e
