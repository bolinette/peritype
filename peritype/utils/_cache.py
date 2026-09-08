import weakref
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from peritype import FWrap, TWrap

_cache_enabled = True


def use_cache(value: bool) -> None:
    global _cache_enabled
    _cache_enabled = value


def type_key(cls: Any) -> Any:
    if isinstance(cls, (int, float, complex, str, bytes, Enum)):
        return (type(cls), cls)
    return cls


class CacheManager:
    def __init__(self) -> None:
        self.twrap_cache: weakref.WeakValueDictionary[Any, TWrap[Any]] = weakref.WeakValueDictionary()
        self.fwrap_cache: weakref.WeakValueDictionary[Any, FWrap[..., Any]] = weakref.WeakValueDictionary()

    def contains_twrap(self, cls: Any) -> bool:
        if not _cache_enabled:
            return False
        try:
            return type_key(cls) in self.twrap_cache
        except TypeError:
            return False

    def contains_fwrap(self, func: Any) -> bool:
        return _cache_enabled and func in self.fwrap_cache

    def get_twrap(self, cls: Any) -> "TWrap[Any]":
        return self.twrap_cache[type_key(cls)]

    def get_fwrap(self, func: Any) -> "FWrap[..., Any]":
        return self.fwrap_cache[func]

    def set_twrap(self, cls: Any, twrap: "TWrap[Any]") -> None:
        if not _cache_enabled:
            return
        try:
            self.twrap_cache[type_key(cls)] = twrap
        except TypeError:
            return

    def set_fwrap(self, func: Any, fwrap: "FWrap[..., Any]") -> None:
        if _cache_enabled:
            self.fwrap_cache[func] = fwrap


CACHE = CacheManager()
