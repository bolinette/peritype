"""``wrap_func`` / ``FWrap`` / ``BoundFWrap``, and function-shaped members of ``TWrap``."""

import inspect
from types import NoneType
from typing import Annotated, Any

import pytest

from peritype import FWrap, wrap_func, wrap_type
from peritype._fwrap import BoundFWrap
from peritype.errors import UnresolvedFunctionTypeVarsError, UnresolvedTypeVarError


def plain(a: int, b: str = "") -> bool:
    return str(a) == b


def no_return(a: int):
    return a


def annotated_param(a: Annotated[int, "meta"]) -> None: ...


def identity[T](value: T) -> T:
    return value


def to_list[T](value: T) -> list[T]:
    return [value]


def two_vars[T, U](a: T, b: U) -> dict[T, U]:
    return {a: b}


def half_inferable[T, U](a: T, b: U) -> list[T]:  # pyright: ignore[reportInvalidTypeVarUse]
    return [a]


class Holder:
    def __init__(self, value: int) -> None:
        self.value = value

    def method(self, x: float) -> bool:
        return x > self.value

    @classmethod
    def build(cls, x: int) -> "Holder":
        return cls(x)

    @staticmethod
    def helper(x: int) -> str:
        return str(x)

    def generic_method[T](self, x: T) -> list[T]:
        return [x]


class GenericHolder[T]:
    def __init__(self, value: T) -> None:
        self.value = value

    def get(self) -> T:
        return self.value

    def put(self, value: T) -> None:
        self.value = value

    def combine[U](self, other: U) -> tuple[T, U]:
        return (self.value, other)


class ConcreteHolder(GenericHolder[str]): ...


class TestPlainFunctions:
    def test_signature_hints(self) -> None:
        hints = wrap_func(plain).get_signature_hints()
        assert set(hints) == {"a", "b", "return"}
        assert hints["a"] == wrap_type(int)
        assert hints["b"] == wrap_type(str)
        assert hints["return"] == wrap_type(bool)

    def test_return_hint(self) -> None:
        assert wrap_func(plain).get_return_hint() == wrap_type(bool)

    def test_hint_by_index(self) -> None:
        assert wrap_func(plain).get_signature_hint(0) == wrap_type(int)
        assert wrap_func(plain).get_signature_hint(1) == wrap_type(str)

    def test_parameters_and_signature(self) -> None:
        w = wrap_func(plain)
        assert w.signature == inspect.signature(plain)
        assert list(w.parameters) == ["a", "b"]
        assert w.param_at(1).default == ""

    def test_names(self) -> None:
        w = wrap_func(plain)
        assert w.name == "plain"
        assert w.qualname == "plain"
        assert str(w) == "plain"
        assert repr(w) == "<Function plain>"
        assert wrap_func(Holder.method).qualname == "Holder.method"

    def test_call_forwards_to_the_function(self) -> None:
        assert wrap_func(plain)(1, "1") is True
        assert wrap_func(plain)(1, b="2") is False

    def test_missing_return_annotation(self) -> None:
        assert "return" not in wrap_func(no_return).get_signature_hints()

    def test_annotated_parameter(self) -> None:
        assert wrap_func(annotated_param).get_signature_hints()["a"].annotations == ("meta",)

    def test_plain_function_is_not_bound(self) -> None:
        assert wrap_func(plain).bound_to is None
        assert wrap_func(plain).func is plain

    def test_bound_method(self) -> None:
        instance = Holder(1)
        w = wrap_func(instance.method)
        assert w.bound_to is instance
        assert list(w.parameters) == ["x"]
        assert w.get_signature_hint(0) == wrap_type(float)

    def test_equality_follows_the_function(self) -> None:
        assert wrap_func(plain) == FWrap(plain)
        assert hash(wrap_func(plain)) == hash(FWrap(plain))
        assert FWrap(plain) != FWrap(no_return)
        assert FWrap(plain) != plain
        assert FWrap(identity) != FWrap(identity).specialize([wrap_type(int)])

    def test_bound_equality_includes_the_owner(self) -> None:
        holder, other = wrap_type(Holder), wrap_type(ConcreteHolder)
        assert wrap_func(Holder.method).bind(holder) == wrap_func(Holder.method).bind(holder)
        assert wrap_func(Holder.method).bind(holder) != wrap_func(Holder.method).bind(other)
        assert wrap_func(Holder.method).bind(holder) != wrap_func(Holder.method)
        assert len({wrap_func(Holder.method).bind(holder), wrap_func(Holder.method).bind(holder)}) == 1

    def test_non_generic_function_is_defined(self) -> None:
        w = wrap_func(plain)
        assert not w.is_generic
        assert w.is_defined
        assert w.type_params == ()
        assert w.specialize([]) is w


class TestGenericFunctions:
    def test_type_params(self) -> None:
        w = wrap_func(identity)
        assert w.is_generic
        assert not w.is_defined
        assert w.type_params == identity.__type_params__

    def test_unspecialised_hints_raise(self) -> None:
        with pytest.raises(UnresolvedTypeVarError):
            wrap_func(identity).get_signature_hints()

    def test_specialize(self) -> None:
        w = wrap_func(identity).specialize([wrap_type(int)])
        assert w.is_defined
        assert w.get_signature_hints()["value"] == wrap_type(int)
        assert w.get_return_hint() == wrap_type(int)

    def test_specialize_does_not_mutate_the_original(self) -> None:
        original = wrap_func(identity)
        original.specialize([wrap_type(int)])
        assert not original.is_defined

    def test_specialize_nested(self) -> None:
        w = wrap_func(to_list).specialize([wrap_type(str)])
        assert w.get_return_hint() == wrap_type(list[str])

    def test_specialize_with_wrong_count(self) -> None:
        with pytest.raises(ValueError, match="does not match"):
            wrap_func(two_vars).specialize([wrap_type(int)])

    def test_unspecialize_uses_any(self) -> None:
        w = wrap_func(two_vars).unspecialize()
        assert w.is_defined
        assert w.get_signature_hints()["a"] == wrap_type(Any)
        assert w.get_return_hint() == wrap_type(dict[Any, Any])

    def test_specialize_from_return(self) -> None:
        w = wrap_func(to_list).specialize_from_return(wrap_type(list[int]))
        assert w.get_signature_hints()["value"] == wrap_type(int)
        assert wrap_func(identity).specialize_from_return(wrap_type(str)).get_return_hint() == wrap_type(str)

    def test_specialize_from_return_with_two_vars(self) -> None:
        w = wrap_func(two_vars).specialize_from_return(wrap_type(dict[str, int]))
        hints = w.get_signature_hints()
        assert hints["a"] == wrap_type(str)
        assert hints["b"] == wrap_type(int)

    def test_specialize_from_return_needs_every_typevar(self) -> None:
        with pytest.raises(UnresolvedFunctionTypeVarsError) as info:
            wrap_func(half_inferable).specialize_from_return(wrap_type(list[int]))
        assert info.value.func_name == "half_inferable"
        assert info.value.typevars == ["T", "U"]

    def test_specialize_from_return_on_non_generic_returns_self(self) -> None:
        w = wrap_func(plain)
        assert w.specialize_from_return(wrap_type(bool)) is w


class TestInit:
    def test_init_is_bound_to_the_type(self) -> None:
        init = wrap_type(Holder).init
        assert isinstance(init, BoundFWrap)
        hints = init.get_signature_hints()
        assert hints["value"] == wrap_type(int)
        assert hints["return"].inner_type is NoneType

    def test_generic_init_resolves_class_typevars(self) -> None:
        assert wrap_type(GenericHolder[int]).init.get_signature_hints()["value"] == wrap_type(int)
        assert wrap_type(GenericHolder).init.get_signature_hints()["value"] == wrap_type(Any)

    def test_inherited_generic_init(self) -> None:
        assert wrap_type(ConcreteHolder).init.get_signature_hints()["value"] == wrap_type(str)

    def test_signature_and_parameters(self) -> None:
        w = wrap_type(Holder)
        assert w.signature == inspect.signature(Holder)
        assert list(w.parameters) == ["value"]
        assert w.nodes[0].signature == w.signature
        assert list(w.nodes[0].parameters) == ["value"]

    def test_signature_of_a_builtin(self) -> None:
        assert list(wrap_type(int).parameters) == ["args", "kwargs"]
        assert wrap_type(int).signature == wrap_type(int).nodes[0].signature
        assert list(wrap_type(list[int]).parameters) == ["iterable"]

    def test_instantiate(self) -> None:
        assert wrap_type(Holder).instantiate(3).value == 3
        assert wrap_type(Holder).instantiate(value=4).value == 4
        assert wrap_type(list[int]).instantiate() == []
        assert wrap_type(GenericHolder[int]).instantiate(1).value == 1


class TestMethods:
    def test_get_method_hints(self) -> None:
        method = wrap_type(Holder).get_method("method")
        assert isinstance(method, BoundFWrap)
        assert method.get_signature_hints()["x"] == wrap_type(float)
        assert method.get_return_hint() == wrap_type(bool)

    def test_missing_method(self) -> None:
        with pytest.raises(AttributeError):
            wrap_type(Holder).get_method("nope")

    def test_classmethod_and_staticmethod(self) -> None:
        build = wrap_type(Holder).get_method("build")
        assert build.get_signature_hints()["x"] == wrap_type(int)
        assert build.get_return_hint() == wrap_type(Holder)
        helper = wrap_type(Holder).get_method("helper")
        assert helper.get_return_hint() == wrap_type(str)

    def test_class_typevars_are_resolved(self) -> None:
        w = wrap_type(GenericHolder[int])
        assert w.get_method("get").get_return_hint() == wrap_type(int)
        assert w.get_method("put").get_signature_hints()["value"] == wrap_type(int)

    def test_inherited_method_uses_the_child_parameters(self) -> None:
        assert wrap_type(ConcreteHolder).get_method("get").get_return_hint() == wrap_type(str)

    def test_unparameterised_class_resolves_to_any(self) -> None:
        assert wrap_type(GenericHolder).get_method("get").get_return_hint() == wrap_type(Any)

    def test_method_typevars_must_be_specialised(self) -> None:
        method = wrap_type(Holder).get_method("generic_method")
        assert method.is_generic
        with pytest.raises(UnresolvedTypeVarError):
            method.get_signature_hints()
        assert method.specialize([wrap_type(int)]).get_return_hint() == wrap_type(list[int])

    def test_method_and_class_typevars_combine(self) -> None:
        holder = wrap_type(GenericHolder[int])
        combine = holder.get_method("combine").specialize([wrap_type(bytes)])
        assert combine.get_return_hint(belongs_to=holder) == wrap_type(tuple[int, bytes])

    def test_explicit_belongs_to_overrides_the_binding(self) -> None:
        method = wrap_type(GenericHolder[int]).get_method("get")
        assert method.get_return_hint(belongs_to=wrap_type(GenericHolder[str])) == wrap_type(str)

    def test_unbound_fwrap_can_be_given_an_owner(self) -> None:
        w: FWrap[..., Any] = wrap_func(GenericHolder[Any].get)
        with pytest.raises(UnresolvedTypeVarError):
            w.get_return_hint()
        assert w.get_return_hint(belongs_to=wrap_type(GenericHolder[int])) == wrap_type(int)
        assert w.bind(wrap_type(GenericHolder[str])).get_return_hint() == wrap_type(str)

    def test_get_method_is_cached(self) -> None:
        w = wrap_type(Holder)
        assert w.get_method("method") is w.get_method("method")
