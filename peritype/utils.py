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

from peritype.errors import UnresolvedForwardRefError, UnresolvedTypeVarError
from peritype.mapping import TypeVarMapping
from peritype.twrap import TWrapMeta


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
    if origin is None:
        return cls
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


def use_cache(value: bool) -> None:
    from peritype import wrap

    wrap.USE_CACHE = value


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
