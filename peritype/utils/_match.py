from dataclasses import dataclass
from typing import Literal

type MatchKind = Literal["exact", "lineage", "catchall", "none"]

_KIND_RANK: dict[MatchKind, int] = {"none": 0, "catchall": 1, "lineage": 2, "exact": 3}


def strongest_kind(a: MatchKind, b: MatchKind) -> MatchKind:
    return a if _KIND_RANK[a] >= _KIND_RANK[b] else b


def weakest_kind(a: MatchKind, b: MatchKind) -> MatchKind:
    return a if _KIND_RANK[a] <= _KIND_RANK[b] else b


@dataclass(slots=True, frozen=True, order=False)
class MatchResult:
    kind: MatchKind

    def __bool__(self) -> bool:
        return self.kind != "none"

    def __lt__(self, other: "MatchResult") -> bool:
        return _KIND_RANK[self.kind] < _KIND_RANK[other.kind]

    def __le__(self, other: "MatchResult") -> bool:
        return _KIND_RANK[self.kind] <= _KIND_RANK[other.kind]

    def __gt__(self, other: "MatchResult") -> bool:
        return _KIND_RANK[self.kind] > _KIND_RANK[other.kind]

    def __ge__(self, other: "MatchResult") -> bool:
        return _KIND_RANK[self.kind] >= _KIND_RANK[other.kind]

    @property
    def is_exact(self) -> bool:
        return self.kind == "exact"

    @property
    def is_lineage(self) -> bool:
        return self.kind == "lineage"

    @property
    def is_catchall(self) -> bool:
        return self.kind == "catchall"

    @property
    def is_none(self) -> bool:
        return self.kind == "none"

    @staticmethod
    def exact() -> "MatchResult":
        return MatchResult("exact")

    @staticmethod
    def lineage() -> "MatchResult":
        return MatchResult("lineage")

    @staticmethod
    def catchall() -> "MatchResult":
        return MatchResult("catchall")

    @staticmethod
    def none() -> "MatchResult":
        return MatchResult("none")
