import collections.abc
import contextlib
from types import UnionType
from typing import (
    Annotated,
    Any,
    ForwardRef,
    NotRequired,
    ParamSpec,
    TypeAliasType,
    TypeVar,
    Union,  # pyright: ignore[reportDeprecated]
    get_args,
    get_origin,
)

from peritype._mapping import TypeVarMapping
from peritype._twrap import TWrapMeta
from peritype.errors import UnresolvedForwardRefError, UnresolvedTypeVarError


def unpack_annotations(cls: Any, meta: TWrapMeta) -> Any:
    if isinstance(cls, TypeAliasType):
        return unpack_annotations(cls.__value__, meta)
    origin = get_origin(cls)
    if origin is Annotated:
        cls, *annotated = get_args(cls)
        meta.annotated = (*annotated,)
        return unpack_annotations(cls, meta)
    if origin is NotRequired:
        meta.required = False
        return unpack_annotations(get_args(cls)[0], meta)
    meta.total = getattr(cls, "__total__", True)
    return cls


def unpack_union(cls: Any) -> tuple[Any, ...]:
    origin = get_origin(cls)
    if origin in (UnionType, Union):  # pyright: ignore[reportDeprecated]
        return get_args(cls)
    else:
        return (cls,)


def get_generics[GenT](
    _cls: type[GenT],
    *,
    raise_on_forward: bool,
    raise_on_typevar: bool,
) -> tuple[type[GenT], tuple[Any, ...]]:
    if origin := get_origin(_cls):
        type_vars: list[Any] = []
        for arg in get_args(_cls):
            arg: Any
            match arg:
                case TypeVar() if raise_on_typevar:
                    raise UnresolvedTypeVarError(arg.__name__, cls=origin)
                case ForwardRef() if raise_on_forward:
                    raise UnresolvedForwardRefError(arg.__forward_arg__, cls=origin)
                case list():
                    arg = (*arg,)
                case _:
                    pass
            type_vars.append(arg)
        return origin, (*type_vars,)
    return _cls, ()


def specialize_type(
    cls: Any,
    lookup: TypeVarMapping,
    *,
    raise_on_forward: bool = True,
    raise_on_typevar: bool = True,
) -> Any:
    origin = get_origin(cls)
    match origin:
        case None:
            return cls
        case _ if isinstance(origin, TypeAliasType):
            return specialize_type(
                cls.__value__,
                # Type aliases redefine their TypeVars, so we need to replace them in the lookup
                lookup.replace_with(cls.__type_params__),
                raise_on_forward=raise_on_forward,
                raise_on_typevar=raise_on_typevar,
            )
        case _ if origin is Annotated:
            base, *annotations = get_args(cls)
            specialized_base = specialize_type(
                base,
                lookup,
                raise_on_forward=raise_on_forward,
                raise_on_typevar=raise_on_typevar,
            )
            return Annotated[specialized_base, *annotations]
        case _ if origin is UnionType or origin is Union:  # pyright: ignore[reportDeprecated]
            args = get_args(cls)
            new_args: list[Any] = []
            for arg in args:
                specialized_arg = specialize_type(
                    arg,
                    lookup,
                    raise_on_forward=raise_on_forward,
                    raise_on_typevar=raise_on_typevar,
                )
                new_args.append(specialized_arg)
            return Union[*new_args]  # pyright: ignore[reportDeprecated]
        case _ if origin is NotRequired:
            base = get_args(cls)[0]
            specialized_base = specialize_type(
                base,
                lookup,
                raise_on_forward=raise_on_forward,
                raise_on_typevar=raise_on_typevar,
            )
            return NotRequired[specialized_base]
        case _:
            pass
    args = get_args(cls)
    if not args:
        return cls
    new_args: list[Any] = []
    specialized = False
    for arg in args:
        match arg:
            case TypeVar() if arg in lookup:
                new_args.append(lookup[arg])
                specialized = True
            case TypeVar() if raise_on_typevar:
                raise UnresolvedTypeVarError(arg.__name__, cls=origin)
            case ForwardRef() if raise_on_forward:
                raise UnresolvedForwardRefError(arg.__forward_arg__, cls=origin)
            case _:
                new_args.append(arg)
    vars = tuple(new_args)
    if not specialized:
        return cls
    return origin[vars]


def find_type_var_equivalents(
    t1: Any,
    t2: Any,
    lookup: dict[TypeVar, Any] | None = None,
) -> dict[TypeVar, Any]:
    if lookup is None:
        lookup = {}
    if isinstance(t1, TypeVar):
        lookup[t1] = t2
        return lookup
    origin1 = get_origin(t1)
    origin2 = get_origin(t2)
    if origin1 != origin2:
        raise ValueError(f"Cannot match types {t1} and {t2}")
    args1 = get_args(t1)
    args2 = get_args(t2)
    for arg1, arg2 in zip(args1, args2, strict=True):
        find_type_var_equivalents(arg1, arg2, lookup=lookup)
    return lookup


def fill_params_in(cls_: type[Any], vars: tuple[Any, ...]) -> tuple[type[Any], tuple[Any, ...]]:
    params: tuple[Any, ...] = getattr(cls_, "__type_params__", None) or getattr(cls_, "__parameters__", None) or ()
    if cls_ in BUILTIN_PARAM_COUNT:
        param_count = BUILTIN_PARAM_COUNT[cls_]
    else:
        param_count = len(params)
    if len(vars) >= param_count:
        return cls_, vars
    new_vars: list[Any] = []
    for i in range(len(vars), param_count):
        if i < len(params):
            if isinstance(params[i], ParamSpec):
                new_vars.append(...)
            else:
                new_vars.append(Any)
        else:
            new_vars.append(Any)
    return cls_, (*vars, *new_vars)


BUILTIN_PARAM_COUNT: dict[type[Any], int] = {
    collections.abc.Hashable: 0,
    collections.abc.Awaitable: 1,
    collections.abc.Coroutine: 3,
    collections.abc.AsyncIterable: 1,
    collections.abc.AsyncIterator: 1,
    collections.abc.Iterable: 1,
    collections.abc.Iterator: 1,
    collections.abc.Reversible: 1,
    collections.abc.Sized: 0,
    collections.abc.Container: 1,
    collections.abc.Collection: 1,
    collections.abc.Set: 1,
    collections.abc.MutableSet: 1,
    collections.abc.Mapping: 2,
    collections.abc.MutableMapping: 2,
    collections.abc.Sequence: 1,
    collections.abc.MutableSequence: 1,
    list: 1,
    collections.deque: 1,
    set: 1,
    frozenset: 1,
    collections.abc.MappingView: 1,
    collections.abc.KeysView: 1,
    collections.abc.ItemsView: 2,
    collections.abc.ValuesView: 1,
    contextlib.AbstractContextManager: 1,
    contextlib.AbstractAsyncContextManager: 1,
    dict: 2,
    collections.defaultdict: 2,
    collections.OrderedDict: 2,
    collections.Counter: 1,
    collections.ChainMap: 2,
    collections.abc.Generator: 3,
    collections.abc.AsyncGenerator: 2,
    type: 1,
}
