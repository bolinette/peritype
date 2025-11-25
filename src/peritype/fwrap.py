import inspect
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, get_type_hints, override

from peritype.twrap import TWrap

if TYPE_CHECKING:
    from peritype.twrap import TWrap, TypeVarLookup


class FWrap[**FuncP, FuncT]:
    def __init__(self, func: Callable[FuncP, FuncT]) -> None:
        if isinstance(func, FWrap):
            raise TypeError(f"Cannot wrap {func}, already wrapped")
        self.func = func
        self.bound_to = getattr(self.func, "__self__", None)
        self._signature_hints: dict[str, Any] | None = None
        self._signature: inspect.Signature | None = None
        self._parameters: dict[str, inspect.Parameter] | None = None

    @property
    def name(self) -> str:
        return self.func.__name__ if hasattr(self.func, "__name__") else str(self.func)

    @property
    def parameters(self) -> dict[str, inspect.Parameter]:
        if self._parameters is None:
            if self._signature is None:
                self._signature = inspect.signature(self.func)
            self._parameters = {**self._signature.parameters}
        return self._parameters

    def param_at(self, index: int) -> inspect.Parameter:
        all_params = [*self.parameters.values()]
        return all_params[index]

    def get_signature_hints(self, belongs_to: "TWrap[Any] | None" = None) -> "dict[str, TWrap[Any]]":
        if self._signature_hints is None:
            self._signature_hints = {
                n: self._transform_annotation(c, belongs_to.type_var_lookup if belongs_to else None)
                for n, c in get_type_hints(self.func, include_extras=True).items()
            }
        return self._signature_hints

    def get_signature_hint(self, index: int, belongs_to: "TWrap[Any] | None" = None) -> "TWrap[Any]":
        return self.get_signature_hints(belongs_to)[self.param_at(index).name]

    def get_return_hint(self, belongs_to: "TWrap[Any] | None" = None) -> "TWrap[FuncT]":
        return self.get_signature_hints(belongs_to)["return"]

    def __call__(self, *args: FuncP.args, **kwargs: FuncP.kwargs) -> FuncT:
        return self.func(*args, **kwargs)

    @staticmethod
    def _transform_annotation(anno: Any, lookup: "TypeVarLookup | None") -> Any:
        from peritype import wrap_type

        if lookup is not None and anno in lookup:
            return wrap_type(lookup[anno], lookup=lookup)
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

    def bind(self, bound_to: "TWrap[Any]") -> "BoundFWrap[FuncP, FuncT]":
        return BoundFWrap(self, bound_to)


class BoundFWrap[**FWrapP, FWrapT]:
    def __init__(self, fwrap: FWrap[FWrapP, FWrapT], bound_to: "TWrap[Any]") -> None:
        self._fwrap = fwrap
        self._bound_to = bound_to

    @property
    def name(self) -> str:
        return self.inner.name

    @property
    def inner(self) -> FWrap[FWrapP, FWrapT]:
        return self._fwrap

    @property
    def bound_to(self) -> "TWrap[Any]":
        return self._bound_to

    @property
    def func(self) -> Callable[FWrapP, FWrapT]:
        return self.inner.func

    @property
    def parameters(self) -> dict[str, inspect.Parameter]:
        return self.inner.parameters

    def param_at(self, index: int) -> inspect.Parameter:
        return self.inner.param_at(index)

    def get_signature_hints(self) -> dict[str, TWrap[Any]]:
        return self._fwrap.get_signature_hints(self._bound_to)

    def get_signature_hint(self, index: int) -> "TWrap[Any]":
        return self.get_signature_hints()[self.param_at(index).name]

    def get_return_hint(self) -> "TWrap[FWrapT]":
        return self.inner.get_return_hint(self.bound_to)

    def __call__(self, *args: FWrapP.args, **kwargs: FWrapP.kwargs) -> FWrapT:  # type: ignore[misc]
        return self.inner(*args, **kwargs)

    @override
    def __str__(self) -> str:
        return str(self.inner)

    @override
    def __repr__(self) -> str:
        return repr(self.inner)

    @override
    def __hash__(self) -> int:
        return hash(self.inner)
