from typing import Any


class PeritypeError(Exception):
    def __init__(self, message: str, cls: type[Any] | None = None) -> None:
        if cls is not None:
            message = f"{cls.__qualname__}: {message}"
        super().__init__(message)
        self.cls = cls
