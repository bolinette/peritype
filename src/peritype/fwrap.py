import inspect
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, get_type_hints, override

if TYPE_CHECKING:
    from peritype.twrap import TWrap, TypeVarLookup


class FWrap[**FuncP, FuncT]:
    def __init__(self, func: Callable[FuncP, FuncT]) -> None:
        if isinstance(func, FWrap):
            raise TypeError(f"Cannot wrap {func}, already wrapped")
        self.func = func
        self.bound_to = getattr(self.func, "__self__", None)
        self._annotations: dict[str, Any] | None = None
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

    def annotations(self, belongs_to: "TWrap[Any] | None" = None) -> "dict[str, TWrap[Any]]":
        if self._annotations is None:
            self._annotations = {
                n: self._transform_annotation(c, belongs_to.type_var_lookup if belongs_to else None)
                for n, c in get_type_hints(self.func, include_extras=True).items()
            }
        return self._annotations

    def annotation(self, index: int) -> "TWrap[Any]":
        return self.annotations()[self.param_at(index).name]

    @property
    def return_type(self) -> "TWrap[FuncT]":
        return self.annotations()["return"]

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
