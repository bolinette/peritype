"""Inheritance: ``bases``, ``iter_bases``, ``lineage="super" | "sub" | "both"``, and ``is_type_of``."""

from typing import Any, Literal, NamedTuple, Protocol, TypedDict, TypeVar, override

import pytest

from peritype import wrap_type
from peritype._twrap import Lineage


class Root: ...


class Mid(Root): ...


class Leaf(Mid): ...


class Other: ...


class Diamond(Mid, Other): ...


class GRoot[T]: ...


class GMid[T](GRoot[T]): ...


class GLeaf[T](GMid[T]): ...


class FixedMid(GRoot[int]): ...


class FixedLeaf(FixedMid): ...


class Swapped[A, B](GRoot[B]): ...


class TestBases:
    def test_direct_base(self) -> None:
        assert wrap_type(Mid).nodes[0].bases == (wrap_type(Root),)

    def test_object_is_the_root(self) -> None:
        assert wrap_type(Root).nodes[0].bases == (wrap_type(object),)

    def test_generic_base_receives_the_child_parameter(self) -> None:
        assert wrap_type(GMid[int]).nodes[0].bases == (wrap_type(GRoot[int]),)
        assert wrap_type(Swapped[int, str]).nodes[0].bases == (wrap_type(GRoot[str]),)

    def test_fixed_generic_base(self) -> None:
        assert wrap_type(FixedMid).nodes[0].bases == (wrap_type(GRoot[int]),)

    def test_multiple_inheritance_keeps_declaration_order(self) -> None:
        assert wrap_type(Diamond).nodes[0].bases == (wrap_type(Mid), wrap_type(Other))

    def test_unparameterised_generic_base_is_any(self) -> None:
        assert wrap_type(GMid).nodes[0].bases == (wrap_type(GRoot[Any]),)

    def test_plain_subclass_of_a_generic_derived_class(self) -> None:
        assert wrap_type(FixedLeaf).nodes[0].bases == (wrap_type(FixedMid),)

    def test_builtin_generic_base(self) -> None:
        class MyDict(dict[str, int]): ...

        class MyList(list[int]): ...

        assert wrap_type(MyDict).nodes[0].bases == (wrap_type(dict[str, int]),)
        assert wrap_type(MyList).nodes[0].bases == (wrap_type(list[int]),)

    def test_a_special_form_has_no_base(self) -> None:
        """Special forms like ``Literal`` are not classes, so there is nothing to walk."""
        assert wrap_type(Literal[1]).nodes[0].bases == ()
        assert list(wrap_type(Literal[1]).iter_bases()) == []

    def test_old_style_protocol_base(self) -> None:
        T_co = TypeVar("T_co", covariant=True)

        class Readable(Protocol[T_co]):
            def read(self) -> T_co: ...

        class IntReader(Readable[int]):
            @override
            def read(self) -> int:
                return 1

        assert wrap_type(IntReader).nodes[0].bases == (wrap_type(Readable[int]),)
        assert wrap_type(IntReader).get_method("read").get_return_hint() == wrap_type(int)


class TestSyntheticBases:
    def test_a_named_tuple_is_walked_through_tuple(self) -> None:
        """``NamedTuple`` is a function at runtime, so the real base is read from ``__bases__``."""

        class Pair(NamedTuple):
            first: int

        assert wrap_type(Pair).nodes[0].bases == (wrap_type(tuple),)
        assert wrap_type(Pair).match(tuple, lineage="super").is_lineage
        assert wrap_type(tuple).is_type_of(Pair(first=1))

    def test_a_generic_named_tuple_is_walked_through_tuple(self) -> None:
        """A parameterized ``NamedTuple`` reaches ``tuple`` like a plain one."""

        class GPair[T](NamedTuple):
            first: T

        assert wrap_type(GPair[int]).nodes[0].bases == (wrap_type(tuple),)

    def test_a_typed_dict_is_walked_through_dict(self) -> None:
        """``TypedDict`` is a function at runtime, so the real base is read from ``__bases__``."""

        class Movie(TypedDict):
            title: str

        assert wrap_type(Movie).nodes[0].bases == (wrap_type(dict),)
        assert wrap_type(Movie).match(dict, lineage="super").is_lineage

    def test_a_typed_dict_keeps_the_typed_dict_it_extends(self) -> None:
        """The fallback only applies to the synthetic base, a real parent is kept."""

        class Movie(TypedDict):
            title: str

        class Film(Movie):
            year: int

        assert wrap_type(Film).nodes[0].bases == (wrap_type(Movie),)
        assert list(wrap_type(Film).iter_bases()) == [wrap_type(Movie), wrap_type(dict), wrap_type(object)]

    def test_protocol_is_not_reported_as_a_base(self) -> None:
        """``Protocol`` is typing machinery, like ``Generic``, and never a base of its own."""

        class Greeter(Protocol):
            def greet(self) -> str: ...

        class Hello(Greeter):
            @override
            def greet(self) -> str:
                return "hi"

        assert wrap_type(Greeter).nodes[0].bases == ()
        assert wrap_type(Hello).nodes[0].bases == (wrap_type(Greeter),)
        assert wrap_type(Hello).match(Greeter, lineage="super").is_lineage


class TestIterBases:
    def test_a_chain_is_walked_to_the_top(self) -> None:
        """``iter_bases`` yields the ancestors of the type, not only its direct bases."""
        assert list(wrap_type(Leaf).iter_bases()) == [wrap_type(Mid), wrap_type(Root), wrap_type(object)]

    def test_the_wrapper_itself_is_never_yielded(self) -> None:
        """Only ancestors are walked, so a type without a base yields nothing."""
        assert wrap_type(Leaf) not in list(wrap_type(Leaf).iter_bases())
        assert list(wrap_type(object).iter_bases()) == []

    def test_type_parameters_are_resolved_along_the_chain(self) -> None:
        """Every ancestor is yielded with the parameters it receives from its child."""
        assert list(wrap_type(GLeaf[int]).iter_bases()) == [wrap_type(GMid[int]), wrap_type(GRoot[int])]
        assert list(wrap_type(FixedLeaf).iter_bases()) == [wrap_type(FixedMid), wrap_type(GRoot[int])]

    def test_breadth_first_is_the_default(self) -> None:
        """The default order yields the closest ancestors first, in declaration order."""
        assert list(wrap_type(Diamond).iter_bases()) == [
            wrap_type(Mid),
            wrap_type(Other),
            wrap_type(Root),
            wrap_type(object),
        ]

    def test_depth_first_follows_each_branch_to_its_end(self) -> None:
        """``"dfs"`` exhausts the first branch before moving to the next one."""
        assert list(wrap_type(Diamond).iter_bases(order="dfs")) == [
            wrap_type(Mid),
            wrap_type(Root),
            wrap_type(object),
            wrap_type(Other),
        ]

    def test_mro_follows_the_class_linearization(self) -> None:
        """``"mro"`` yields the ancestors in the same order as ``__mro__``, without the type itself."""
        assert [b.origin for b in wrap_type(Diamond).iter_bases(order="mro")] == list(Diamond.__mro__[1:])

    def test_mro_keeps_the_resolved_parameters(self) -> None:
        """The linearization is filled in with the specializations found while walking the bases."""
        assert list(wrap_type(GLeaf[int]).iter_bases(order="mro")) == [
            wrap_type(GMid[int]),
            wrap_type(GRoot[int]),
            wrap_type(object),
        ]

    def test_mro_reaches_object_through_a_generic_class(self) -> None:
        """``Generic`` stops the base graph, so only the linearization reaches ``object``."""
        assert wrap_type(object) not in list(wrap_type(GLeaf[int]).iter_bases())
        assert wrap_type(object) in list(wrap_type(GLeaf[int]).iter_bases(order="mro"))

    def test_a_base_reached_twice_is_yielded_once(self) -> None:
        """A base shared by two branches is yielded the first time it is reached."""

        class Fork1(Mid): ...

        class Fork2(Mid): ...

        class Join(Fork1, Fork2): ...

        assert list(wrap_type(Join).iter_bases()) == [
            wrap_type(Fork1),
            wrap_type(Fork2),
            wrap_type(Mid),
            wrap_type(Root),
            wrap_type(object),
        ]

    def test_a_union_walks_every_member(self) -> None:
        """Each node of a union contributes its own ancestors, without repeating a shared one."""
        assert list(wrap_type(Mid | Other).iter_bases()) == [wrap_type(Root), wrap_type(object)]

    def test_a_base_can_be_searched_by_match(self) -> None:
        """Searching the walk gives the ancestor with its parameters, which matching alone cannot."""
        base = next((b for b in wrap_type(FixedLeaf).iter_bases() if b.matches(GRoot[Any])), None)

        assert base == wrap_type(GRoot[int])
        assert base is not None
        assert base.generic_params == (wrap_type(int),)


class TestDirectLineage:
    @pytest.mark.parametrize(
        ("lineage", "child_to_parent", "parent_to_child"),
        [
            ("none", "none", "none"),
            ("super", "lineage", "none"),
            ("sub", "none", "lineage"),
            ("both", "lineage", "lineage"),
        ],
    )
    def test_direction(self, lineage: Lineage, child_to_parent: str, parent_to_child: str) -> None:
        assert wrap_type(Mid).match(Root, lineage=lineage).kind == child_to_parent
        assert wrap_type(Root).match(Mid, lineage=lineage).kind == parent_to_child

    def test_default_is_no_lineage(self) -> None:
        assert wrap_type(Mid).match(Root).is_none
        assert not wrap_type(Mid).matches(Root)

    def test_same_type_is_still_exact_with_lineage(self) -> None:
        assert wrap_type(Mid).match(Mid, lineage="both").is_exact

    @pytest.mark.parametrize("lineage", ["none", "super", "sub", "both"])
    def test_unrelated_types_stay_none(self, lineage: Lineage) -> None:
        assert wrap_type(Other).match(Root, lineage=lineage).is_none
        assert wrap_type(Root).match(Other, lineage=lineage).is_none

    def test_generic_parameters_propagate_to_the_parent(self) -> None:
        assert wrap_type(GMid[int]).match(GRoot[int], lineage="super").is_lineage
        assert wrap_type(GMid[str]).match(GRoot[int], lineage="super").is_none
        assert wrap_type(GRoot[int]).match(GMid[int], lineage="sub").is_lineage
        assert wrap_type(GRoot[int]).match(GMid[str], lineage="sub").is_none

    def test_swapped_parameters_follow_the_declaration(self) -> None:
        assert wrap_type(Swapped[int, str]).match(GRoot[str], lineage="super").is_lineage
        assert wrap_type(Swapped[int, str]).match(GRoot[int], lineage="super").is_none

    def test_fixed_parameter_in_the_parent(self) -> None:
        assert wrap_type(FixedMid).match(GRoot[int], lineage="super").is_lineage
        assert wrap_type(FixedMid).match(GRoot[str], lineage="super").is_none
        assert wrap_type(GRoot[int]).match(FixedMid, lineage="sub").is_lineage

    def test_lineage_is_only_as_strong_as_its_parameters(self) -> None:
        assert wrap_type(GMid[int]).match(GRoot[Any], lineage="super").is_catchall
        assert wrap_type(GMid[int]).match(GRoot[int | str], lineage="super").is_lineage
        assert wrap_type(GMid[int]).match(GRoot[Any], lineage="super", strict=True).is_none

    def test_multiple_inheritance_reaches_every_base(self) -> None:
        assert wrap_type(Diamond).match(Mid, lineage="super").is_lineage
        assert wrap_type(Diamond).match(Other, lineage="super").is_lineage
        assert wrap_type(Other).match(Diamond, lineage="sub").is_lineage

    def test_lineage_against_a_union(self) -> None:
        assert wrap_type(Mid).match(Root | str, lineage="super").is_lineage
        assert wrap_type(Mid | int).match(Root, lineage="super").is_lineage
        assert wrap_type(Mid | Root).match(Root, lineage="super").is_exact


class TestDeepLineage:
    def test_grandchild_matches_grandparent(self) -> None:
        assert wrap_type(Leaf).match(Root, lineage="super").is_lineage
        assert wrap_type(Root).match(Leaf, lineage="sub").is_lineage
        assert wrap_type(Leaf).match(Root, lineage="both").is_lineage

    def test_generic_grandchild_matches_grandparent(self) -> None:
        assert wrap_type(GLeaf[int]).match(GRoot[int], lineage="super").is_lineage
        assert wrap_type(GLeaf[str]).match(GRoot[int], lineage="super").is_none

    def test_plain_grandchild_of_generic_root(self) -> None:
        assert wrap_type(FixedLeaf).match(FixedMid, lineage="super").is_lineage
        assert wrap_type(FixedLeaf).match(GRoot[int], lineage="super").is_lineage


class TestIsTypeOf:
    @pytest.mark.parametrize(
        ("cls", "value", "expected"),
        [
            (int, 1, True),
            (int, "a", False),
            (int, True, True),
            (str, "a", True),
            (int | str, 1, True),
            (int | str, 1.5, False),
            (int | None, None, True),
            (int, None, False),
            (None, None, True),
            (Any, object(), True),
            (Root, Root(), True),
            (Root, Mid(), True),
            (Mid, Root(), False),
            (Other, Diamond(), True),
        ],
    )
    def test_plain_values(self, cls: Any, value: Any, expected: bool) -> None:
        assert wrap_type(cls).is_type_of(value) is expected

    def test_generic_instances_carry_their_parameters(self) -> None:
        assert wrap_type(GRoot[int]).is_type_of(GRoot[int]())
        assert not wrap_type(GRoot[int]).is_type_of(GRoot[str]())
        assert wrap_type(GRoot[str]).is_type_of(Swapped[int, str]())
        assert not wrap_type(GRoot[str]).is_type_of(Swapped[str, int]())

    def test_any_parameters_are_lax_unless_strict(self) -> None:
        assert wrap_type(GRoot[Any]).is_type_of(GRoot[int]())
        assert wrap_type(GRoot[int]).is_type_of(GRoot[Any]())
        assert wrap_type(GRoot[int]).is_type_of(GRoot())
        assert not wrap_type(GRoot[Any]).is_type_of(GRoot[int](), strict=True)
        assert not wrap_type(GRoot[int]).is_type_of(GRoot[Any](), strict=True)
        assert not wrap_type(GRoot[int]).is_type_of(GRoot(), strict=True)

    def test_container_contents_are_not_inspected(self) -> None:
        # The runtime type of a list is ``list``, which wraps as ``list[Any]``.
        assert wrap_type(list[int]).is_type_of([1, 2])
        assert wrap_type(list[int]).is_type_of(["a"])
        assert not wrap_type(list[int]).is_type_of([1, 2], strict=True)

    def test_returns_a_bool(self) -> None:
        assert wrap_type(int).is_type_of(1) is True
        assert wrap_type(int).is_type_of("a") is False

    def test_grandchild_instance(self) -> None:
        assert wrap_type(Root).is_type_of(Leaf())
        assert wrap_type(GRoot[int]).is_type_of(GLeaf[int]())

    def test_instance_of_plain_subclass_of_generic_derived_class(self) -> None:
        assert wrap_type(FixedMid).is_type_of(FixedLeaf())

    def test_instance_of_builtin_generic_subclass(self) -> None:
        class MyDict(dict[str, int]): ...

        assert wrap_type(dict[str, int]).is_type_of(MyDict())
