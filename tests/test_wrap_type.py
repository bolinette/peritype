"""``wrap_type``: construction and introspection of ``TWrap`` objects."""

from types import NoneType
from typing import (
    Annotated,
    Any,
    ClassVar,
    Final,
    ForwardRef,
    List,
    NotRequired,
    Optional,
    ReadOnly,
    Required,
    TypedDict,
    TypeVar,
    Union,
)

import pytest

from peritype import TWrap, wrap_type
from peritype.errors import UnresolvedForwardRefError, UnresolvedTypeVarError


class Plain: ...


class Generic1[T]: ...


class Generic2[T, U]: ...


class WithParamSpec[**P]: ...


class WithAttrs:
    a: int
    b: str | None
    c: list[Plain]


class WithInheritedAttrs(WithAttrs):
    d: float


class Empty: ...


class Complete(TypedDict):
    x: int
    y: NotRequired[str]


class Partial(TypedDict, total=False):
    x: Required[int]
    y: int
    z: ReadOnly[str]


type IntList = list[int]
type Alias[X] = list[X]
type AliasOfAlias[Y] = dict[Y, Alias[Y]]
type InnerAnnotated = Annotated[int, "inner"]

UnboundT = TypeVar("UnboundT")


class TestSimpleTypes:
    @pytest.mark.parametrize("cls", [int, str, float, bool, bytes, Plain])
    def test_wraps_a_class(self, cls: type[Any]) -> None:
        w = wrap_type(cls)
        assert isinstance(w, TWrap)
        assert w.origin is cls
        assert w.inner_type is cls
        assert len(w.nodes) == 1
        assert w[0] is w.nodes[0]
        assert w.nodes[0].inner_type is cls
        assert not w.union
        assert not w.nullable
        assert not w.contains_any
        assert w.generic_params == ()
        assert w.annotations == ()
        assert w.required
        assert w.total

    @pytest.mark.parametrize(
        ("cls", "expected"),
        [
            (int, "int"),
            (Plain, "Plain"),
            (list[int], "list[int]"),
            (dict[str, list[int]], "dict[str, list[int]]"),
            (int | str, "int | str"),
            (int | None, "int | NoneType"),
            (Any, "Any"),
            (list, "list[Any]"),
            (WithParamSpec, "WithParamSpec[...]"),
        ],
    )
    def test_str(self, cls: Any, expected: str) -> None:
        assert str(wrap_type(cls)) == expected

    def test_repr(self) -> None:
        assert repr(wrap_type(int)) == "<Type int>"
        assert repr(wrap_type(list[int])) == "<Type list[int]>"

    def test_same_type_wraps_are_equal(self) -> None:
        assert wrap_type(int) == wrap_type(int)
        assert hash(wrap_type(int)) == hash(wrap_type(int))
        assert wrap_type(int) != wrap_type(str)
        assert wrap_type(int) != object()


class TestNone:
    @pytest.mark.parametrize("value", [None, NoneType])
    def test_none_is_nullable_and_not_a_union(self, value: Any) -> None:
        w = wrap_type(value)
        assert w.nullable
        assert not w.union
        assert w.inner_type is NoneType
        assert str(w) == "NoneType"

    def test_none_and_nonetype_are_the_same_wrap(self) -> None:
        assert wrap_type(None) == wrap_type(NoneType)

    def test_none_has_no_attributes(self) -> None:
        assert wrap_type(None).attribute_hints == {}


class TestUnions:
    def test_two_members(self) -> None:
        w = wrap_type(int | str)
        assert w.union
        assert not w.nullable
        assert len(w.nodes) == 2
        assert {n.inner_type for n in w.nodes} == {int, str}

    def test_optional_is_nullable_but_not_a_union(self) -> None:
        w = wrap_type(int | None)
        assert not w.union
        assert w.nullable
        assert len(w.nodes) == 2

    def test_union_with_none_is_both(self) -> None:
        w = wrap_type(int | str | None)
        assert w.union
        assert w.nullable

    @pytest.mark.parametrize(
        ("a", "b"),
        [
            (int | str, str | int),
            (int | None, Optional[int]),
            (int | None, Union[int, None]),
            (Union[int, str], int | str),
            (int | str | None, None | str | int),
        ],
    )
    def test_equivalent_spellings_are_equal(self, a: Any, b: Any) -> None:
        assert wrap_type(a) == wrap_type(b)
        assert hash(wrap_type(a)) == hash(wrap_type(b))

    @pytest.mark.parametrize(
        "accessor",
        ["inner_type", "generic_params", "attribute_hints", "init", "signature", "parameters"],
    )
    def test_single_type_accessors_reject_unions(self, accessor: str) -> None:
        with pytest.raises(TypeError):
            getattr(wrap_type(int | str), accessor)

    def test_instantiate_and_get_method_reject_unions(self) -> None:
        with pytest.raises(TypeError):
            wrap_type(int | str).instantiate()
        with pytest.raises(TypeError):
            wrap_type(int | str).get_method("__init__")

    def test_optional_exposes_the_non_none_member(self) -> None:
        w = wrap_type(WithAttrs | None)
        assert w.inner_type is WithAttrs
        assert set(w.attribute_hints) == {"a", "b", "c"}

    def test_optional_with_none_first_exposes_the_non_none_member(self) -> None:
        w = wrap_type(None | WithAttrs)
        assert w.inner_type is WithAttrs
        assert set(w.attribute_hints) == {"a", "b", "c"}


class TestGenericParameters:
    def test_builtin_generic(self) -> None:
        w = wrap_type(list[int])
        assert w.inner_type is list
        assert w.origin == list[int]
        assert len(w.generic_params) == 1
        assert w.generic_params[0] == wrap_type(int)

    def test_nested_generic(self) -> None:
        w = wrap_type(dict[str, list[int]])
        assert w.generic_params[0] == wrap_type(str)
        assert w.generic_params[1] == wrap_type(list[int])
        assert w[0][1] == wrap_type(list[int])

    def test_unparameterised_builtin_is_filled_with_any(self) -> None:
        bare_list: Any = list
        w = wrap_type(bare_list)
        assert w.generic_params[0].inner_type is Any
        assert w.contains_any
        assert w == wrap_type(list[Any])

    def test_unparameterised_mapping_gets_two_parameters(self) -> None:
        assert wrap_type(dict) == wrap_type(dict[Any, Any])

    def test_unparameterised_user_generic_is_filled_with_any(self) -> None:
        assert wrap_type(Generic1) == wrap_type(Generic1[Any])
        assert wrap_type(Generic2) == wrap_type(Generic2[Any, Any])

    def test_unparameterised_paramspec_is_filled_with_ellipsis(self) -> None:
        w = wrap_type(WithParamSpec)
        assert w.generic_params[0].inner_type is Ellipsis
        assert w == wrap_type(WithParamSpec[...])

    def test_typing_alias_equals_builtin(self) -> None:
        assert wrap_type(List[int]) == wrap_type(list[int])

    def test_contains_any_is_recursive(self) -> None:
        assert wrap_type(dict[str, list[Any]]).contains_any
        assert not wrap_type(dict[str, list[int]]).contains_any
        assert wrap_type(int | Any).contains_any

    def test_explicit_typevar_is_rejected(self) -> None:
        unbound: Any = UnboundT
        with pytest.raises(UnresolvedTypeVarError):
            wrap_type(list[unbound])
        with pytest.raises(UnresolvedTypeVarError):
            wrap_type(Generic1[unbound])

    def test_forward_ref_is_rejected(self) -> None:
        with pytest.raises(UnresolvedForwardRefError):
            wrap_type(list[ForwardRef("Missing")])

    def test_bare_typevar_is_rejected(self) -> None:
        with pytest.raises(UnresolvedTypeVarError):
            wrap_type(UnboundT)

    def test_wrapping_a_wrap_returns_it(self) -> None:
        w = wrap_type(list[int])
        assert wrap_type(w) is w


class TestAnnotated:
    def test_metadata_is_exposed(self) -> None:
        w = wrap_type(Annotated[int, "a", 2])
        assert w.annotations == ("a", 2)
        assert w.inner_type is int
        assert w.match(int).is_exact

    def test_annotated_wrap_differs_from_bare_wrap(self) -> None:
        assert wrap_type(Annotated[int, "a"]) != wrap_type(int)
        assert wrap_type(Annotated[int, "a"]) != wrap_type(Annotated[int, "b"])
        assert wrap_type(Annotated[int, "a"]) == wrap_type(Annotated[int, "a"])

    def test_annotated_optional(self) -> None:
        w = wrap_type(Annotated[int | None, "m"])
        assert w.nullable
        assert not w.union
        assert w.annotations == ("m",)

    def test_not_required(self) -> None:
        assert not wrap_type(NotRequired[int]).required
        assert wrap_type(NotRequired[int]).inner_type is int
        assert wrap_type(int).required

    def test_annotated_inside_union_member(self) -> None:
        w = wrap_type(Optional[Annotated[int, "a"]])
        assert w.matches(int)
        assert w.inner_type is int
        assert w.annotations == ("a",)

    def test_annotations_accumulate_across_members(self) -> None:
        w = wrap_type(Union[Annotated[int, "a"], Annotated[str, "b"]])
        assert w.union
        assert w.annotations == ("a", "b")
        assert w.match(int | str).is_exact

    def test_nested_annotations_keep_the_inner_first(self) -> None:
        assert wrap_type(Annotated[InnerAnnotated, "outer"]).annotations == ("inner", "outer")
        assert wrap_type(Annotated[Annotated[int, "inner"], "outer"]).annotations == ("inner", "outer")


class TestTypedDict:
    def test_total(self) -> None:
        assert wrap_type(Complete).total
        assert not wrap_type(Partial).total
        assert not wrap_type(Partial | None).total
        assert not wrap_type(None | Partial).total

    def test_required_flags(self) -> None:
        attrs = wrap_type(Complete).attribute_hints
        assert attrs["x"].required
        assert attrs["x"].matches(int)
        assert not attrs["y"].required
        assert attrs["y"].matches(str)

    def test_required_in_partial_typed_dict(self) -> None:
        attrs = wrap_type(Partial).attribute_hints
        assert attrs["x"].inner_type is int
        assert attrs["z"].inner_type is str
        assert attrs["z"] == wrap_type(str)
        assert attrs["x"].required


class TestTypeAliases:
    def test_plain_alias_is_transparent(self) -> None:
        w = wrap_type(IntList)
        assert w == wrap_type(list[int])
        assert w.match(list[int]).is_exact

    def test_parameterised_alias_is_transparent(self) -> None:
        w = wrap_type(Alias[int])
        assert w.match(list[int]).is_exact
        assert w.inner_type is list
        assert w == wrap_type(list[int])

    def test_bare_generic_alias_is_filled_with_any(self) -> None:
        assert wrap_type(Alias) == wrap_type(list[Any])

    def test_alias_of_alias(self) -> None:
        assert wrap_type(AliasOfAlias[str]) == wrap_type(dict[str, list[str]])
        assert wrap_type(Annotated[AliasOfAlias[int], "m"]).annotations == ("m",)


class TestAttributeHints:
    def test_hints_are_wrapped(self) -> None:
        attrs = wrap_type(WithAttrs).attribute_hints
        assert set(attrs) == {"a", "b", "c"}
        assert attrs["a"] == wrap_type(int)
        assert attrs["b"].nullable
        assert attrs["b"].inner_type is str
        assert attrs["c"] == wrap_type(list[Plain])

    def test_inherited_hints_are_included(self) -> None:
        attrs = wrap_type(WithInheritedAttrs).attribute_hints
        assert set(attrs) == {"a", "b", "c", "d"}

    def test_class_without_annotations(self) -> None:
        assert wrap_type(Empty).attribute_hints == {}

    def test_class_var_and_final_are_transparent(self) -> None:
        class WithQualifiers:
            counter: ClassVar[int] = 0
            name: Final[str] = "x"
            flag: Final = True

        attrs = wrap_type(WithQualifiers).attribute_hints
        assert attrs["counter"] == wrap_type(int)
        assert attrs["name"] == wrap_type(str)
        assert attrs["flag"] == wrap_type(Any)

    def test_unresolvable_forward_ref_raises(self) -> None:
        class Broken:
            x: "Missing"  # noqa: F821  # pyright: ignore[reportUndefinedVariable]
            y: int

        with pytest.raises(UnresolvedForwardRefError) as info:
            _ = wrap_type(Broken).attribute_hints
        assert info.value.name == "Missing"
        assert info.value.cls is Broken
