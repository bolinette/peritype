"""Inheritance: ``bases``, ``lineage="super" | "sub" | "both"``, and ``is_type_of``."""

from typing import Any, Protocol, TypeVar, override

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
