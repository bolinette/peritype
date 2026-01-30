import weakref
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from peritype import FWrap, TWrap

USE_CACHE = True


def use_cache(value: bool) -> None:
    use_cache.__globals__["USE_CACHE"] = value


class CacheManager:
    def __init__(self) -> None:
        self.twrap_cache: weakref.WeakValueDictionary[Any, TWrap[Any]] = weakref.WeakValueDictionary()
        self.fwrap_cache: weakref.WeakValueDictionary[Any, FWrap[..., Any]] = weakref.WeakValueDictionary()

    def contains_twrap(self, cls: Any) -> bool:
        return USE_CACHE and cls in self.twrap_cache

    def contains_fwrap(self, func: Any) -> bool:
        return USE_CACHE and func in self.fwrap_cache

    def get_twrap(self, cls: Any) -> "TWrap[Any]":
        return self.twrap_cache[cls]

    def get_fwrap(self, func: Any) -> "FWrap[..., Any]":
        return self.fwrap_cache[func]

    def set_twrap(self, cls: Any, twrap: "TWrap[Any]") -> None:
        if USE_CACHE:
            self.twrap_cache[cls] = twrap

    def set_fwrap(self, func: Any, fwrap: "FWrap[..., Any]") -> None:
        if USE_CACHE:
            self.fwrap_cache[func] = fwrap


CACHE = CacheManager()
