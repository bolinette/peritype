from typing import Any, Generic, Protocol, TypeGuard, TypeVar, get_origin


class WithOriginBases(Protocol):
    __orig_bases__: tuple[type[Any], ...]

    @staticmethod
    def match(_obj: Any) -> "TypeGuard[WithOriginBases]":
        return hasattr(_obj, "__orig_bases__")

    @staticmethod
    def get_origin_bases(_obj: Any) -> tuple[type[Any], ...]:
        return tuple(base for base in _obj.__orig_bases__ if get_origin(base) not in (None, Generic))


class WithOriginClass(Protocol):
    __orig_class__: type[Any]

    @staticmethod
    def match(_obj: Any) -> "TypeGuard[WithOriginClass]":
        return hasattr(_obj, "__orig_class__")


class WithParameters(Protocol):
    __parameters__: tuple[TypeVar, ...]

    @staticmethod
    def match(_obj: type[Any], *, check_len: bool = False) -> "TypeGuard[WithParameters]":
        return hasattr(_obj, "__parameters__") and (not check_len or len(_obj.__parameters__) > 0)


class WithTypeParams(Protocol):
    __type_params__: tuple[TypeVar, ...]

    @staticmethod
    def match(_obj: type[Any], *, check_len: bool = False) -> "TypeGuard[WithTypeParams]":
        return hasattr(_obj, "__type_params__") and (not check_len or len(_obj.__type_params__) > 0)


class WithArgs(Protocol):
    __args__: tuple[type[Any], ...]

    @staticmethod
    def match(_obj: type[Any], *, check_len: bool = False) -> "TypeGuard[WithArgs]":
        return hasattr(_obj, "__args__") and (not check_len or len(_obj.__args__) > 0)


def is_generic(cls: type[Any]) -> bool:
    return (
        WithTypeParams.match(cls, check_len=True)
        or WithParameters.match(cls, check_len=True)
        or WithArgs.match(cls, check_len=True)
    )
