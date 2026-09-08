"""TypeVar resolution through inheritance: ``attribute_hints`` and ``type_var_lookup``."""

from collections.abc import Callable
from typing import Any, Generic, TypeVar, cast

import pytest

from peritype import wrap_type
from peritype._twrap import TypeVarLookup
from peritype.errors import UnresolvedTypeVarError


class Parent[T]:
    value: T
    items: list[T]


class Child(Parent[int]):
    extra: str


class GenericChild[U](Parent[U]):
    other: U


class Transversal[A, B](Parent[B]):
    first: A


class Deep[X](GenericChild[X]): ...


OldT = TypeVar("OldT")


class OldStyle(Generic[OldT]):  # noqa: UP046 — the pre-PEP 695 spelling is the point
    value: OldT


type Alias[X] = list[X]


class UsesAlias[U]:
    x: Alias[U]


class UsesAliasWithTwoVars[U, V]:
    x: Alias[V]


PARENT_T = cast(TypeVar, Parent.__type_params__[0])
GENERIC_CHILD_U = cast(TypeVar, GenericChild.__type_params__[0])


class TestAttributeHints:
    def test_concrete_child_resolves_parent_typevar(self) -> None:
        attrs = wrap_type(Child).attribute_hints
        assert attrs["value"] == wrap_type(int)
        assert attrs["items"] == wrap_type(list[int])
        assert attrs["extra"] == wrap_type(str)

    def test_parameterised_generic_child(self) -> None:
        attrs = wrap_type(GenericChild[str]).attribute_hints
        assert attrs["value"] == wrap_type(str)
        assert attrs["items"] == wrap_type(list[str])
        assert attrs["other"] == wrap_type(str)

    def test_transversal_typevars(self) -> None:
        attrs = wrap_type(Transversal[int, str]).attribute_hints
        assert attrs["first"] == wrap_type(int)
        assert attrs["value"] == wrap_type(str)
        assert attrs["items"] == wrap_type(list[str])

    def test_deep_chain(self) -> None:
        attrs = wrap_type(Deep[bytes]).attribute_hints
        assert attrs["value"] == wrap_type(bytes)
        assert attrs["other"] == wrap_type(bytes)
        assert attrs["items"] == wrap_type(list[bytes])

    def test_unparameterised_resolves_to_any(self) -> None:
        attrs = wrap_type(Parent).attribute_hints
        assert attrs["value"] == wrap_type(Any)
        assert attrs["items"] == wrap_type(list[Any])

    def test_parameterised_directly(self) -> None:
        attrs = wrap_type(Parent[float]).attribute_hints
        assert attrs["value"] == wrap_type(float)

    def test_old_style_generic(self) -> None:
        assert wrap_type(OldStyle[int]).attribute_hints["value"] == wrap_type(int)
        assert wrap_type(OldStyle).attribute_hints["value"] == wrap_type(Any)

    def test_typevar_nested_in_a_generic_attribute(self) -> None:
        class Nested[T]:
            mapping: dict[str, list[T]]

        assert wrap_type(Nested[int]).attribute_hints["mapping"] == wrap_type(dict[str, list[int]])

    def test_typevar_inside_a_callable_signature(self) -> None:
        class Handler[T]:
            handle: Callable[[T], int]
            build: Callable[..., T]

        attrs = wrap_type(Handler[str]).attribute_hints
        assert attrs["handle"] == wrap_type(Callable[[str], int])
        assert attrs["build"] == wrap_type(Callable[..., str])

    def test_generic_alias_with_one_class_typevar(self) -> None:
        assert wrap_type(UsesAlias[int]).attribute_hints["x"] == wrap_type(list[int])

    def test_generic_alias_with_two_class_typevars(self) -> None:
        assert wrap_type(UsesAliasWithTwoVars[int, str]).attribute_hints["x"] == wrap_type(list[str])


class TestTypeVarLookup:
    def test_lookup_of_a_parameterised_type(self) -> None:
        lookup = wrap_type(Parent[int]).type_var_lookup
        assert PARENT_T in lookup
        assert lookup[PARENT_T] is int
        assert lookup.get_twrap(PARENT_T) == wrap_type(int)
        assert len(lookup) == 1
        assert list(lookup) == [PARENT_T]

    def test_child_lookup_includes_parent_typevars(self) -> None:
        lookup = wrap_type(GenericChild[str]).type_var_lookup
        assert GENERIC_CHILD_U in lookup
        assert PARENT_T in lookup
        assert lookup[GENERIC_CHILD_U] is str
        assert lookup[PARENT_T] is str

    def test_missing_typevar(self) -> None:
        lookup = wrap_type(Parent[int]).type_var_lookup
        assert GENERIC_CHILD_U not in lookup
        with pytest.raises(KeyError):
            lookup[GENERIC_CHILD_U]
        with pytest.raises(KeyError):
            lookup.get_twrap(GENERIC_CHILD_U)

    def test_non_generic_type_has_an_empty_lookup(self) -> None:
        assert len(wrap_type(int).type_var_lookup) == 0

    def test_union_lookup_merges_members(self) -> None:
        lookup = wrap_type(Parent[int] | GenericChild[str]).type_var_lookup
        assert lookup[PARENT_T] is int or lookup[PARENT_T] is str
        assert GENERIC_CHILD_U in lookup

    def test_keys_must_match(self) -> None:
        with pytest.raises(ValueError, match="same TypeVar keys"):
            TypeVarLookup({PARENT_T: int}, {})


class TestExplicitLookup:
    def test_wrap_type_with_lookup_specialises_typevars(self) -> None:
        lookup = TypeVarLookup({PARENT_T: int}, {PARENT_T: wrap_type(int)})
        assert wrap_type(list[PARENT_T], lookup=lookup) == wrap_type(list[int])
        assert wrap_type(dict[str, PARENT_T], lookup=lookup) == wrap_type(dict[str, int])
        assert wrap_type(Parent[PARENT_T] | None, lookup=lookup) == wrap_type(Parent[int] | None)

    def test_wrap_type_with_lookup_specialises_nested_typevars(self) -> None:
        lookup = TypeVarLookup({PARENT_T: int}, {PARENT_T: wrap_type(int)})
        assert wrap_type(dict[str, list[PARENT_T]], lookup=lookup) == wrap_type(dict[str, list[int]])

    def test_unknown_typevar_in_lookup_raises(self) -> None:
        lookup = TypeVarLookup({PARENT_T: int}, {PARENT_T: wrap_type(int)})
        with pytest.raises(UnresolvedTypeVarError):
            wrap_type(list[GENERIC_CHILD_U], lookup=lookup)

    def test_bare_typevar_is_resolved_from_the_lookup(self) -> None:
        lookup = TypeVarLookup({PARENT_T: int}, {PARENT_T: wrap_type(int)})
        assert wrap_type(PARENT_T, lookup=lookup) == wrap_type(int)

    def test_lookup_without_typevars_is_a_no_op(self) -> None:
        lookup = TypeVarLookup({PARENT_T: int}, {PARENT_T: wrap_type(int)})
        assert wrap_type(list[str], lookup=lookup) == wrap_type(list[str])
