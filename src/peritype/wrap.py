from collections.abc import Callable
from types import UnionType
from typing import Any, cast, overload

from peritype import FWrap, TWrap
from peritype.mapping import TypeVarMapping
from peritype.twrap import TWrapMeta, TypeNode
from peritype.utils import get_generics, unpack_annotations, unpack_union

USE_CACHE = True
_WRAP_CACHE: dict[Any, TWrap[Any]] = {}


@overload
def wrap_type[T](
    cls: type[T],
    *,
    lookup: TypeVarMapping | None = None,
) -> TWrap[T]: ...
@overload
def wrap_type(
    cls: UnionType,
    *,
    lookup: TypeVarMapping | None = None,
) -> TWrap[Any]: ...
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
    if USE_CACHE and cls in _WRAP_CACHE:
        return _WRAP_CACHE[cls]
    meta = TWrapMeta(annotated=tuple(), required=True, total=True)
    unpacked: Any = unpack_annotations(cls, meta)
    nodes = unpack_union(unpacked)
    wrapped_nodes: list[Any] = []
    for node in nodes:
        if node in (None, type(None)):
            node = type(None)
        root, vars = get_generics(node, lookup, True, True)
        wrapped_vars = tuple(wrap_type(var) for var in vars)
        wrapped_node = TypeNode(node, wrapped_vars, root, vars)
        wrapped_nodes.append(wrapped_node)
    twrap = cast(TWrap[Any], TWrap(origin=cls, nodes=(*wrapped_nodes,), meta=meta))
    if USE_CACHE:
        _WRAP_CACHE[cls] = twrap
    return twrap


def wrap_func[**FuncP, FuncT](
    func: Callable[FuncP, FuncT],
) -> FWrap[FuncP, FuncT]:
    from peritype.fwrap import FWrap

    return FWrap(func)
