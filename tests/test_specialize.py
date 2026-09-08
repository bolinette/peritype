"""``TWrap.specialize_with``: filling a generic wrap's parameters from another wrap."""

from typing import Annotated, Any

import pytest

from peritype import wrap_type
from peritype.errors import IncompatibleTypesError


class Box[T]: ...


class SubBox[T](Box[T]): ...


class Pair[K, V]: ...


class Other[T]: ...


class TestSpecializeWith:
    def test_from_the_same_generic(self) -> None:
        specialised = wrap_type(Box).specialize_with(wrap_type(Box[int]))
        assert specialised == wrap_type(Box[int])
        assert specialised.origin == Box[int]
        assert specialised.generic_params == (wrap_type(int),)

    def test_two_parameters(self) -> None:
        assert wrap_type(Pair).specialize_with(wrap_type(Pair[str, int])) == wrap_type(Pair[str, int])

    def test_child_from_parent(self) -> None:
        assert wrap_type(SubBox).specialize_with(wrap_type(Box[int])) == wrap_type(SubBox[int])

    def test_parent_from_child(self) -> None:
        assert wrap_type(Box).specialize_with(wrap_type(SubBox[int])) == wrap_type(Box[int])

    def test_specialising_keeps_the_source_untouched(self) -> None:
        bare_box: Any = Box
        source = wrap_type(bare_box)
        source.specialize_with(wrap_type(Box[int]))
        assert source == wrap_type(Box[Any])
        assert source.generic_params[0].inner_type is Any

    def test_result_matches_like_a_fresh_wrap(self) -> None:
        specialised = wrap_type(Box).specialize_with(wrap_type(Box[int]))
        assert specialised.match(Box[int]).is_exact
        assert specialised.match(Box[str]).is_none
        assert wrap_type(Box[int]).match(specialised).is_exact

    def test_incompatible_generics_raise(self) -> None:
        with pytest.raises(IncompatibleTypesError) as info:
            wrap_type(Box).specialize_with(wrap_type(Other[int]))
        assert info.value.c1 is Box
        assert info.value.c2 == Other[int]

    def test_nested_parameters_are_preserved(self) -> None:
        specialised = wrap_type(Box).specialize_with(wrap_type(Box[list[int]]))
        assert specialised == wrap_type(Box[list[int]])
        assert specialised.origin == Box[list[int]]
        bare_list: Any = list
        assert wrap_type(Box[bare_list]).generic_params == (wrap_type(list[Any]),)

    def test_annotations_do_not_leak_into_the_cache(self) -> None:
        bare_box: Any = Box
        specialised = wrap_type(Annotated[bare_box, "meta"]).specialize_with(wrap_type(Box[int]))
        assert specialised.annotations == ("meta",)
        assert wrap_type(Box[int]).annotations == ()

    def test_union_with_a_non_generic_member(self) -> None:
        specialised = wrap_type(int | Box).specialize_with(wrap_type(Box[int]))
        assert specialised == wrap_type(int | Box[int])

    def test_incompatible_union_raises_a_peritype_error(self) -> None:
        with pytest.raises(IncompatibleTypesError):
            wrap_type(Box | Other).specialize_with(wrap_type(Pair[int, int]))
