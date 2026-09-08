"""The matching algebra: ``match`` / ``matches``, ``strict``, and ``MatchResult``."""

from collections.abc import Callable
from typing import Any, Literal

import pytest

from peritype import wrap_type
from peritype.utils import MatchKind, MatchResult, strongest_kind, weakest_kind


class Plain: ...


class Generic1[T]: ...


class Generic2[T, U]: ...


class WithParamSpec[**P]: ...


REPRESENTATIVE_TYPES: list[Any] = [
    int,
    str,
    Plain,
    None,
    Any,
    list[int],
    dict[str, list[int]],
    Generic1[int],
    Generic2[int, str],
    int | str,
    int | None,
    tuple[int, str],
    Callable[[int], str],
    Literal["a"],
    WithParamSpec[int, str],
]

UNRELATED_PAIRS: list[tuple[Any, Any]] = [
    (int, str),
    (int, Plain),
    (int, None),
    (list[int], list[str]),
    (list[int], set[int]),
    (dict[str, int], list[int]),
    (Generic1[int], Generic2[int, int]),
    (Generic1[int], Generic1[str]),
    (tuple[int, str], tuple[str, int]),
    (Literal["a"], Literal["b"]),
    (Literal["a"], str),
    (Callable[[int], str], Callable[[str], str]),
    (WithParamSpec[int, str], WithParamSpec[str, int]),
    (int | str, float),
]


class TestLaws:
    @pytest.mark.parametrize("cls", REPRESENTATIVE_TYPES)
    def test_every_type_matches_itself_exactly(self, cls: Any) -> None:
        assert wrap_type(cls).match(cls).is_exact
        assert wrap_type(cls).match(cls, strict=True).is_exact

    @pytest.mark.parametrize(("a", "b"), UNRELATED_PAIRS)
    def test_unrelated_types_never_match(self, a: Any, b: Any) -> None:
        assert wrap_type(a).match(b).is_none
        assert wrap_type(b).match(a).is_none
        assert not wrap_type(a).matches(b)
        assert not wrap_type(b).matches(a)

    def test_raw_type_and_wrap_argument_are_equivalent(self) -> None:
        w = wrap_type(list[int])
        assert w.match(list[int]) == w.match(wrap_type(list[int]))
        assert w.match(str) == w.match(wrap_type(str))

    def test_matches_is_the_truthiness_of_match(self) -> None:
        assert wrap_type(int).matches(int) is True
        assert wrap_type(int).matches(str) is False
        assert wrap_type(int).matches(Any) is True
        assert wrap_type(int).matches(Any, strict=True) is False


class TestAny:
    def test_any_is_a_catchall_in_both_directions(self) -> None:
        assert wrap_type(int).match(Any).is_catchall
        assert wrap_type(Any).match(int).is_catchall
        assert wrap_type(Any).match(int | str).is_catchall

    def test_strict_mode_rejects_any(self) -> None:
        assert wrap_type(int).match(Any, strict=True).is_none
        assert wrap_type(Any).match(int, strict=True).is_none

    def test_any_matches_any_exactly(self) -> None:
        assert wrap_type(Any).match(Any).is_exact
        assert wrap_type(Any).match(Any, strict=True).is_exact

    def test_any_as_a_generic_parameter(self) -> None:
        assert wrap_type(list[int]).match(list[Any]).is_catchall
        assert wrap_type(list[Any]).match(list[int]).is_catchall
        assert wrap_type(list[Any]).match(list[Any]).is_exact
        assert wrap_type(list[int]).match(list[Any], strict=True).is_none

    def test_unparameterised_generic_behaves_as_any(self) -> None:
        assert wrap_type(list[int]).match(list).is_catchall
        assert wrap_type(Generic1[int]).match(Generic1).is_catchall


class TestUnions:
    def test_member_matches_union_exactly(self) -> None:
        assert wrap_type(int).match(int | str).is_exact
        assert wrap_type(int | str).match(int).is_exact
        assert wrap_type(int | str).match(int | float).is_exact

    def test_no_common_member_is_none(self) -> None:
        assert wrap_type(int | str).match(float).is_none
        assert wrap_type(int | str).match(float | bytes).is_none

    def test_optional_matches_none_and_member(self) -> None:
        assert wrap_type(int | None).match(None).is_exact
        assert wrap_type(int | None).match(int).is_exact
        assert wrap_type(int).match(int | None).is_exact
        assert wrap_type(int).match(None).is_none

    def test_strongest_member_wins(self) -> None:
        assert wrap_type(Any | int).match(int).is_exact
        assert wrap_type(int | Any).match(int).is_exact
        assert wrap_type(int).match(Any | int).is_exact
        assert wrap_type(str | list[Any]).match(list[int]).is_catchall

    def test_strict_union(self) -> None:
        assert wrap_type(int | str).match(int, strict=True).is_exact
        assert wrap_type(Any | str).match(int, strict=True).is_none


class TestGenerics:
    def test_parameters_are_matched_recursively(self) -> None:
        assert wrap_type(list[int]).match(list[int | str]).is_exact
        assert wrap_type(list[int | str]).match(list[int]).is_exact
        assert wrap_type(dict[str, list[int]]).match(dict[str, list[int]]).is_exact

    def test_weakest_parameter_decides(self) -> None:
        assert wrap_type(dict[str, list[Any]]).match(dict[str, list[int]]).is_catchall
        assert wrap_type(dict[str, Any]).match(dict[str, int]).is_catchall
        assert wrap_type(dict[Any, int]).match(dict[str, str]).is_none

    def test_different_arity_is_none(self) -> None:
        assert wrap_type(Generic1[int]).match(Generic2[int, int]).is_none

    def test_different_generic_classes_are_none(self) -> None:
        assert wrap_type(Generic1[int]).match(list[int]).is_none


class TestParamSpecAndEllipsis:
    def test_ellipsis_is_a_catchall_for_parameter_lists(self) -> None:
        assert wrap_type(WithParamSpec[...]).match(WithParamSpec[int, str]).is_catchall
        assert wrap_type(WithParamSpec[int, str]).match(WithParamSpec[...]).is_catchall

    def test_ellipsis_matches_ellipsis_exactly(self) -> None:
        assert wrap_type(WithParamSpec[...]).match(WithParamSpec[...]).is_exact
        assert wrap_type(WithParamSpec[...]).match(WithParamSpec[...], strict=True).is_exact

    def test_strict_rejects_ellipsis(self) -> None:
        assert wrap_type(WithParamSpec[...]).match(WithParamSpec[int, str], strict=True).is_none
        assert wrap_type(WithParamSpec[int, str]).match(WithParamSpec[...], strict=True).is_none

    def test_callable_with_ellipsis(self) -> None:
        assert wrap_type(Callable[..., int]).match(Callable[[str], int]).is_catchall
        assert wrap_type(Callable[..., int]).match(Callable[[str], str]).is_none


class TestLiterals:
    def test_same_value_matches(self) -> None:
        assert wrap_type(Literal["a"]).match(Literal["a"]).is_exact
        assert wrap_type(Literal[1, 2]).match(Literal[1, 2]).is_exact

    def test_literal_does_not_match_its_base_type(self) -> None:
        assert wrap_type(Literal["a"]).match(str).is_none
        assert wrap_type(str).match(Literal["a"]).is_none

    def test_bool_and_int_literals_are_distinct(self) -> None:
        assert wrap_type(Literal[1]).match(Literal[True]).is_none
        assert wrap_type(Literal[True]).match(Literal[1]).is_none
        assert wrap_type(Literal[1]).match(Literal[1.0]).is_none
        assert wrap_type(Literal[1]) != wrap_type(Literal[True])
        assert len({wrap_type(Literal[1]), wrap_type(Literal[True]), wrap_type(Literal[1.0])}) == 3


class TestMatchResult:
    def test_kind_properties(self) -> None:
        assert MatchResult("exact").is_exact
        assert MatchResult("lineage").is_lineage
        assert MatchResult("catchall").is_catchall
        assert MatchResult("none").is_none
        assert not MatchResult("exact").is_none

    def test_factories(self) -> None:
        assert MatchResult.exact() == MatchResult("exact")
        assert MatchResult.lineage() == MatchResult("lineage")
        assert MatchResult.catchall() == MatchResult("catchall")
        assert MatchResult.none() == MatchResult("none")

    def test_truthiness(self) -> None:
        assert MatchResult.exact()
        assert MatchResult.lineage()
        assert MatchResult.catchall()
        assert not MatchResult.none()

    def test_ordering(self) -> None:
        none, catchall, lineage, exact = (
            MatchResult.none(),
            MatchResult.catchall(),
            MatchResult.lineage(),
            MatchResult.exact(),
        )
        assert none < catchall < lineage < exact
        assert exact > lineage > catchall > none
        assert MatchResult.none() <= none <= catchall
        assert MatchResult.exact() >= exact >= lineage
        assert max(none, lineage, catchall) is lineage
        assert min(exact, catchall, lineage) is catchall

    def test_ordering_comes_from_real_matches(self) -> None:
        class Parent: ...

        class Child(Parent): ...

        none = wrap_type(int).match(str)
        catchall = wrap_type(int).match(Any)
        lineage = wrap_type(Child).match(Parent, lineage="super")
        exact = wrap_type(int).match(int)
        assert none < catchall < lineage < exact

    @pytest.mark.parametrize(
        ("a", "b", "strongest", "weakest"),
        [
            ("none", "exact", "exact", "none"),
            ("catchall", "lineage", "lineage", "catchall"),
            ("lineage", "exact", "exact", "lineage"),
            ("exact", "exact", "exact", "exact"),
            ("none", "catchall", "catchall", "none"),
        ],
    )
    def test_strongest_and_weakest_kind(
        self, a: MatchKind, b: MatchKind, strongest: MatchKind, weakest: MatchKind
    ) -> None:
        assert strongest_kind(a, b) == strongest
        assert strongest_kind(b, a) == strongest
        assert weakest_kind(a, b) == weakest
        assert weakest_kind(b, a) == weakest
