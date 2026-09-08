from typing import Any


class PeritypeError(Exception):
    def __init__(self, message: str, cls: Any = None) -> None:
        if cls is not None:
            name = cls.__qualname__ if isinstance(cls, type) else repr(cls)
            message = f"{name}: {message}"
        super().__init__(message)
        self.cls = cls


class UnresolvedForwardRefError(PeritypeError):
    def __init__(self, name: str, cls: type[Any] | None = None) -> None:
        super().__init__(f"Parameter {name} could not be resolved from context", cls=cls)
        self.name = name


class UnresolvedTypeVarError(PeritypeError):
    def __init__(self, typevar_name: str, cls: type[Any] | None = None) -> None:
        super().__init__(f"TypeVar {typevar_name} could not be inferred from context", cls=cls)
        self.typevar_name = typevar_name


class IncompatibleTypesError(PeritypeError):
    def __init__(self, c1: Any, c2: Any) -> None:
        super().__init__(f"Incompatible with type {c2}", cls=c1)
        self.c1 = c1
        self.c2 = c2


class UnresolvedFunctionTypeVarsError(PeritypeError):
    def __init__(self, func_name: str, typevars: list[str]) -> None:
        super().__init__(f"TypeVars {', '.join(typevars)} in function {func_name} could not be inferred from context")
        self.func_name = func_name
        self.typevars = typevars
