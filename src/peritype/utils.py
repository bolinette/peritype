from types import UnionType
from typing import (
    Annotated,
    Any,
    ForwardRef,
    NotRequired,
    TypeAliasType,
    TypeVar,
    Union,  # pyright: ignore[reportDeprecated]
    get_args,
    get_origin,
)

from peritype.errors import PeritypeError
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
    return cls


def unpack_union(cls: Any) -> tuple[Any, ...]:
    origin = get_origin(cls)
    if origin in (UnionType, Union):  # pyright: ignore[reportDeprecated]
        return get_args(cls)
    else:
        return (cls,)


def get_generics[GenT](
    _cls: type[GenT],
    lookup: TypeVarMapping | None,
    raise_on_forward: bool,
    raise_on_typevar: bool,
) -> tuple[type[GenT], tuple[Any, ...]]:
    if origin := get_origin(_cls):
        type_vars: list[Any] = []
        for arg in get_args(_cls):
            arg: Any
            if isinstance(arg, ForwardRef) and raise_on_forward:
                raise PeritypeError(
                    f"Generic parameter '{arg.__forward_arg__}' cannot be a string",
                    cls=origin,
                )
            if isinstance(arg, TypeVar):
                if lookup is not None:
                    if arg in lookup:
                        arg = lookup[arg]
                    elif raise_on_typevar:
                        raise PeritypeError(
                            f"TypeVar ~{arg.__name__} could not be found in lookup",
                            cls=origin,
                        )
                elif raise_on_typevar:
                    raise PeritypeError(
                        f"Generic parameter ~{arg.__name__} cannot be a TypeVar",
                        cls=origin,
                    )
            if isinstance(arg, list):
                arg = (*arg,)
            type_vars.append(arg)
        return origin, (*type_vars,)
    return _cls, ()


def substitute_typevars(arg: Any, lookup: dict[TypeVar, Any]) -> Any:
    if isinstance(arg, TypeVar):
        return lookup.get(arg, arg)
    origin = get_origin(arg)
    if origin is None:
        return arg
    args = tuple(substitute_typevars(a, lookup) for a in get_args(arg))
    try:
        return origin[*args]
    except Exception:
        return arg


def use_cache(value: bool) -> None:
    from peritype import wrap

    wrap.USE_CACHE = value
