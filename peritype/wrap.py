import weakref
from collections.abc import Callable
from typing import Any, cast, overload

from peritype import FWrap, TWrap
from peritype.mapping import TypeVarMapping
from peritype.twrap import TWrapMeta, TypeNode
from peritype.utils import fill_params_in, get_generics, unpack_annotations, unpack_union

USE_CACHE = True
_TWRAP_CACHE: weakref.WeakValueDictionary[Any, TWrap[Any]] = weakref.WeakValueDictionary()
_FWRAP_CACHE: weakref.WeakValueDictionary[Any, FWrap[..., Any]] = weakref.WeakValueDictionary()


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
    if USE_CACHE and cls in _TWRAP_CACHE:
        return _TWRAP_CACHE[cls]
    meta = TWrapMeta(annotated=tuple[Any](), required=True, total=True)
    unpacked: Any = unpack_annotations(cls, meta)
    nodes = unpack_union(unpacked)
    wrapped_nodes: list[Any] = []
    for node in nodes:
        if node in (None, type(None)):
            node = type(None)
        root, vars = get_generics(node, lookup, True, True)
        root, vars = fill_params_in(root, vars)
        wrapped_vars = (*(wrap_type(var) for var in vars),)
        wrapped_node = TypeNode(node, wrapped_vars, root, vars)
        wrapped_nodes.append(wrapped_node)
    twrap = cast(TWrap[Any], TWrap(origin=cls, nodes=(*wrapped_nodes,), meta=meta))
    if USE_CACHE:
        _TWRAP_CACHE[cls] = twrap
    return twrap


def wrap_func[**FuncP, FuncT](
    func: Callable[FuncP, FuncT],
) -> FWrap[FuncP, FuncT]:
    if USE_CACHE and func in _FWRAP_CACHE:
        return _FWRAP_CACHE[func]
    fwrap = FWrap(func)
    if USE_CACHE:
        _FWRAP_CACHE[func] = fwrap
    return fwrap
