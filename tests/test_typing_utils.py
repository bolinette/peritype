"""Helpers exposed by ``peritype.utils``."""

from typing import Any

import pytest

from peritype.utils import WithOriginClass, WithParameters, WithTypeParams, is_generic
from peritype.utils._typing import WithArgs, WithOriginBases


class Plain: ...


class Generic1[T]: ...


class Child(Generic1[int]): ...


class TestIsGeneric:
    @pytest.mark.parametrize("cls", [Generic1, Generic1[int], list[int], dict[str, Any]])
    def test_generic_types(self, cls: Any) -> None:
        assert is_generic(cls)

    @pytest.mark.parametrize("cls", [Plain, int, list, Child])
    def test_non_generic_types(self, cls: Any) -> None:
        assert not is_generic(cls)

    def test_instance_class_of_a_parameterised_generic(self) -> None:
        assert is_generic(type(Generic1[str]()))


class TestProtocols:
    def test_type_params(self) -> None:
        # Each call narrows its argument through the TypeGuard, hence the fresh variables.
        generic: type[Any] = Generic1
        plain: type[Any] = Plain
        assert WithTypeParams.match(generic)
        assert WithTypeParams.match(Generic1, check_len=True)
        assert WithTypeParams.match(plain)
        assert not WithTypeParams.match(Plain, check_len=True)

    def test_parameters(self) -> None:
        assert WithParameters.match(Generic1, check_len=True)
        assert not WithParameters.match(Plain)

    def test_args(self) -> None:
        assert WithArgs.match(Generic1[int], check_len=True)
        assert not WithArgs.match(Generic1)

    def test_origin_class(self) -> None:
        assert WithOriginClass.match(Generic1[int]())
        assert not WithOriginClass.match(Generic1())
        assert not WithOriginClass.match(Plain())

    def test_origin_bases(self) -> None:
        assert WithOriginBases.match(Child)
        assert WithOriginBases.get_origin_bases(Child) == (Generic1[int],)
        assert not WithOriginBases.match(Plain)
