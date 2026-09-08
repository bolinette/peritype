"""The error hierarchy in ``peritype.errors``."""

from typing import Any

import pytest

from peritype.errors import (
    IncompatibleTypesError,
    PeritypeError,
    UnresolvedForwardRefError,
    UnresolvedFunctionTypeVarsError,
    UnresolvedTypeVarError,
)


class Plain: ...


class TestPeritypeError:
    def test_plain_message(self) -> None:
        err = PeritypeError("boom")
        assert str(err) == "boom"
        assert err.cls is None

    def test_message_is_prefixed_with_the_class(self) -> None:
        err = PeritypeError("boom", cls=Plain)
        assert str(err) == "Plain: boom"
        assert err.cls is Plain

    @pytest.mark.parametrize(
        "err",
        [
            UnresolvedForwardRefError("X"),
            UnresolvedTypeVarError("T"),
            IncompatibleTypesError(int, str),
            UnresolvedFunctionTypeVarsError("f", ["T"]),
        ],
    )
    def test_every_error_is_a_peritype_error(self, err: PeritypeError) -> None:
        assert isinstance(err, PeritypeError)
        assert isinstance(err, Exception)


class TestSpecificErrors:
    def test_unresolved_forward_ref(self) -> None:
        err = UnresolvedForwardRefError("Missing", cls=Plain)
        assert err.name == "Missing"
        assert err.cls is Plain
        assert "Missing" in str(err)
        assert str(err).startswith("Plain: ")

    def test_unresolved_typevar(self) -> None:
        err = UnresolvedTypeVarError("T", cls=Plain)
        assert err.typevar_name == "T"
        assert "T" in str(err)
        assert str(err).startswith("Plain: ")

    def test_incompatible_types(self) -> None:
        err = IncompatibleTypesError(Plain, int)
        assert err.c1 is Plain
        assert err.c2 is int
        assert err.cls is Plain
        assert str(err).startswith("Plain: ")
        assert "int" in str(err)

    def test_unresolved_function_typevars(self) -> None:
        err = UnresolvedFunctionTypeVarsError("build", ["T", "U"])
        assert err.func_name == "build"
        assert err.typevars == ["T", "U"]
        assert "T, U" in str(err)
        assert "build" in str(err)

    def test_incompatible_types_accepts_non_class_origins(self) -> None:
        union: Any = int | str
        err = IncompatibleTypesError(union, list[int])
        assert err.c1 == union
        assert str(err).startswith("int | str: ")
        assert "list[int]" in str(err)
