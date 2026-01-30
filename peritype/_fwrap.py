import inspect
from collections.abc import Callable, Collection
from functools import cached_property
from typing import TYPE_CHECKING, Any, TypeVar, get_type_hints, override

from peritype._twrap import TWrap
from peritype.errors import UnresolvedFunctionTypeVarsError, UnresolvedTypeVarError
from peritype.utils._generics import find_type_var_equivalents

if TYPE_CHECKING:
    from peritype._twrap import TWrap, TypeVarLookup


class FWrap[**FuncP, FuncT]:
    def __init__(self, func: Callable[FuncP, FuncT], lookup: "TypeVarLookup | None" = None) -> None:
        self.func = func
        self.bound_to = getattr(self.func, "__self__", None)
        self._signature_hints: dict[TWrap[Any] | None, dict[str, Any]] = {}
        self._type_var_lookup = lookup

    @cached_property
    def name(self) -> str:
        return self.func.__name__ if hasattr(self.func, "__name__") else str(self.func)

    @cached_property
    def qualname(self) -> str:
        return self.func.__qualname__ if hasattr(self.func, "__qualname__") else str(self.func)

    @cached_property
    def signature(self) -> inspect.Signature:
        return inspect.signature(self.func)

    @cached_property
    def parameters(self) -> dict[str, inspect.Parameter]:
        return {**self.signature.parameters}

    @cached_property
    def type_params(self) -> tuple[TypeVar, ...]:
        parameters = getattr(self.func, "__type_params__", None)
        return parameters if parameters is not None else ()

    @cached_property
    def is_generic(self) -> bool:
        return len(self.type_params) > 0

    @cached_property
    def is_defined(self) -> bool:
        if self.is_generic:
            return self._type_var_lookup is not None and len(self._type_var_lookup) == len(self.type_params)
        return True

    def param_at(self, index: int) -> inspect.Parameter:
        all_params = [*self.parameters.values()]
        return all_params[index]

    def get_signature_hints(self, belongs_to: "TWrap[Any] | None" = None) -> "dict[str, TWrap[Any]]":
        from peritype._twrap import TypeVarLookup

        if belongs_to not in self._signature_hints:
            match (belongs_to, self._type_var_lookup):
                case (TWrap(), None):
                    lookup = belongs_to.type_var_lookup
                case (None, TypeVarLookup()):
                    lookup = self._type_var_lookup
                case (TWrap(), TypeVarLookup()):
                    lookup = self._type_var_lookup | belongs_to.type_var_lookup
                case _:
                    lookup = None
            self._signature_hints[belongs_to] = {
                n: self._transform_annotation(c, lookup) for n, c in get_type_hints(self.func).items()
            }
        return self._signature_hints[belongs_to]

    def get_signature_hint(self, index: int, belongs_to: "TWrap[Any] | None" = None) -> "TWrap[Any]":
        return self.get_signature_hints(belongs_to)[self.param_at(index).name]

    def get_return_hint(self, belongs_to: "TWrap[Any] | None" = None) -> "TWrap[FuncT]":
        return self.get_signature_hints(belongs_to)["return"]

    def __call__(self, *args: FuncP.args, **kwargs: FuncP.kwargs) -> FuncT:
        return self.func(*args, **kwargs)

    @staticmethod
    def _transform_annotation(anno: Any, lookup: "TypeVarLookup | None") -> Any:
        from peritype import wrap_type

        if isinstance(anno, TypeVar):
            if lookup is not None and anno in lookup:
                return wrap_type(lookup[anno], lookup=lookup)
            raise UnresolvedTypeVarError(anno.__name__)
        return wrap_type(anno, lookup=lookup)

    @override
    def __str__(self) -> str:
        return f"{self.func.__qualname__}"

    @override
    def __repr__(self) -> str:
        return f"<Function {self}>"

    @override
    def __hash__(self) -> int:
        return hash(self.func)

    def bind(self, belongs_to: "TWrap[Any]") -> "BoundFWrap[FuncP, FuncT]":
        return BoundFWrap(self.func, belongs_to)

    def specialize(self, params: Collection[TWrap[Any]]) -> "FWrap[FuncP, FuncT]":
        from peritype._twrap import TypeVarLookup

        if not self.is_generic:
            return self
        if len(params) != len(self.type_params):
            raise ValueError("Number of specialization parameters does not match number of type parameters")
        lookup = {tv: p for tv, p in zip(self.type_params, params, strict=True)}
        origin_lookup = {tv: p.origin for tv, p in lookup.items()}
        return FWrap(self.func, lookup=TypeVarLookup(origin_lookup, lookup))

    def unspecialize(self) -> "FWrap[FuncP, FuncT]":
        from peritype import wrap_type
        from peritype._twrap import TypeVarLookup

        wrap_any = wrap_type(Any)
        origin_lookup = {tv: Any for tv in self.type_params}
        twrap_lookup = {tv: wrap_any for tv in self.type_params}
        return FWrap(self.func, TypeVarLookup(origin_lookup, twrap_lookup))

    def specialize_from_return(self, return_type: TWrap[FuncT]) -> "FWrap[FuncP, FuncT]":
        from peritype import wrap_type

        if not self.is_generic:
            return self
        hints = get_type_hints(self.func)
        return_anno = hints.get("return", Any)
        type_var_equivalents = find_type_var_equivalents(return_anno, return_type.origin)
        if len(type_var_equivalents) != len(self.type_params):
            raise UnresolvedFunctionTypeVarsError(self.qualname, [tv.__name__ for tv in self.type_params])
        return self.specialize([wrap_type(type_var_equivalents[tv]) for tv in self.type_params])


class BoundFWrap[**FuncP, FuncT](FWrap[FuncP, FuncT]):
    def __init__(self, func: Callable[FuncP, FuncT], belongs_to: "TWrap[Any]") -> None:
        super().__init__(func)
        self._belongs_to = belongs_to

    @override
    def get_signature_hints(self, belongs_to: "TWrap[Any] | None" = None) -> "dict[str, TWrap[Any]]":
        return super().get_signature_hints(belongs_to=belongs_to or self._belongs_to)

    @override
    def get_signature_hint(self, index: int, belongs_to: "TWrap[Any] | None" = None) -> "TWrap[Any]":
        return super().get_signature_hint(index, belongs_to=belongs_to or self._belongs_to)

    @override
    def get_return_hint(self, belongs_to: "TWrap[Any] | None" = None) -> "TWrap[FuncT]":
        return super().get_return_hint(belongs_to=belongs_to or self._belongs_to)
