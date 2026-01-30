from collections.abc import Callable
from typing import Any, cast, overload

from peritype import FWrap, TWrap
from peritype._mapping import TypeVarMapping
from peritype._twrap import TWrapMeta, TypeNode
from peritype.utils._cache import CACHE
from peritype.utils._generics import (
    fill_params_in,
    get_generics,
    specialize_type,
    unpack_annotations,
    unpack_union,
)


@overload
def wrap_type[T](
    cls: type[T],
    *,
    lookup: TypeVarMapping | None = None,
) -> TWrap[T]: ...
@overload
def wrap_type(
    cls: Any,
    *,
    lookup: TypeVarMapping | None = None,
) -> TWrap[Any]: ...
def wrap_type(
    cls: Any,
    *,
    lookup: TypeVarMapping | None = None,
) -> Any:
    if lookup is not None:
        cls = specialize_type(cls, lookup, raise_on_forward=True, raise_on_typevar=True)
    if CACHE.contains_twrap(cls):
        return CACHE.get_twrap(cls)
    meta = TWrapMeta(annotated=tuple[Any](), required=True, total=True)
    unpacked: Any = unpack_annotations(cls, meta)
    nodes = unpack_union(unpacked)
    wrapped_nodes: list[Any] = []
    for node in nodes:
        if node in (None, type(None)):
            node = type(None)
        root, vars = get_generics(node, raise_on_forward=True, raise_on_typevar=True)
        root, vars = fill_params_in(root, vars)
        wrapped_vars = (*(wrap_type(var) for var in vars),)
        wrapped_node = TypeNode(node, wrapped_vars, root, vars)
        wrapped_nodes.append(wrapped_node)
    twrap = cast(TWrap[Any], TWrap(origin=cls, nodes=(*wrapped_nodes,), meta=meta))
    CACHE.set_twrap(cls, twrap)
    return twrap


def wrap_func[**FuncP, FuncT](
    func: Callable[FuncP, FuncT],
) -> FWrap[FuncP, FuncT]:
    if CACHE.contains_fwrap(func):
        return CACHE.get_fwrap(func)
    fwrap = FWrap(func)
    CACHE.set_fwrap(func, fwrap)
    return fwrap
