from collections.abc import Coroutine
from dataclasses import dataclass
from typing import Annotated, Any, Concatenate, NotRequired, Protocol, runtime_checkable

import pytest

from peritype import TWrap, wrap_type
from peritype.errors import IncompatibleTypesError


def test_wrap_basic_type() -> None:
    t_int = wrap_type(int)
    assert isinstance(t_int, TWrap)


def test_wrap_complex_type() -> None:
    class GenericType[T]:
        pass

    t_int = wrap_type(GenericType[int])
    assert isinstance(t_int, TWrap)


def test_type_union() -> None:
    t_union = wrap_type(int | str)
    assert isinstance(t_union, TWrap)
    assert t_union.union
    assert not t_union.nullable

    t_nullable = wrap_type(int | None)
    assert isinstance(t_nullable, TWrap)
    assert not t_nullable.union
    assert t_nullable.nullable


def test_match_union_to_type() -> None:
    assert wrap_type(int | str).match(int)


def test_match_type_to_union() -> None:
    assert wrap_type(str).match(int | str)


def test_match_nested_union_in_generics() -> None:
    assert wrap_type(str | list[str]).match(list[str | int])


def test_match_dict_with_union_args() -> None:
    assert wrap_type(dict[int | str, bool | str | int]).match(dict[str, str])


def test_match_any() -> None:
    assert wrap_type(int).match(Any)
    assert wrap_type(list[Any]).match(list[int])
    assert wrap_type(list[int]).match(list[Any])
    assert wrap_type(dict[str, Any]).match(dict[str, int])
    assert wrap_type(dict[str, int]).match(dict[str, Any])
    assert wrap_type(dict[Any, str]).match(dict[int, str])
    assert wrap_type(dict[int, str]).match(dict[Any, str])


def test_match_none() -> None:
    assert wrap_type(int | None).match(None)
    assert wrap_type(int | None).match(int)
    assert wrap_type(int | None).match(int | None)
    assert wrap_type(None).match(None)
    assert wrap_type(None).match(int | None)
    assert not wrap_type(int).match(None)
    assert not wrap_type(None).match(int)


def test_match_ellipsis() -> None:
    class TestType[**T]: ...

    assert wrap_type(TestType[...]).match(TestType[int, str])
    assert wrap_type(TestType[int, str]).match(TestType[...])

    assert wrap_type(TestType[Concatenate[int, ...]]).match(TestType[Concatenate[int, ...]])
    assert not wrap_type(TestType[Concatenate[str, ...]]).match(TestType[Concatenate[int, ...]])
    assert not wrap_type(TestType[Concatenate[str, ...]]).match(TestType[Concatenate[int, ...]])


def test_wrap_contains_any() -> None:
    assert wrap_type(int).contains_any is False
    assert wrap_type(Any).contains_any is True
    assert wrap_type(list[int]).contains_any is False
    assert wrap_type(list[Any]).contains_any is True
    assert wrap_type(dict[str, Any]).contains_any is True
    assert wrap_type(dict[Any, str]).contains_any is True
    assert wrap_type(list[int | Any]).contains_any is True
    assert wrap_type(list[int | str]).contains_any is False
    assert wrap_type(int | str | Any).contains_any is True
    assert wrap_type(int | str).contains_any is False
    assert wrap_type(list[list[dict[str, Any]]]).contains_any is True
    assert wrap_type(list[list[dict[str, int]]]).contains_any is False


def test_wrap_missing_var_is_any() -> None:
    class TestType[T]: ...

    assert wrap_type(TestType) == wrap_type(TestType[Any])
    assert wrap_type(Coroutine) == wrap_type(Coroutine[Any, Any, Any])

    class TestType2[**P]: ...

    assert wrap_type(TestType2) == wrap_type(TestType2[...])


def test_wrap_paramspec_contains_any() -> None:
    class TestType[**P, T]: ...

    assert wrap_type(TestType[[str, int], int]).contains_any is False
    assert wrap_type(TestType[[str, Any], int]).contains_any is True
    assert wrap_type(TestType[[str, int], Any]).contains_any is True
    assert wrap_type(TestType[..., int]).contains_any is True


def test_wrap_hash() -> None:
    assert hash(wrap_type(int)) == hash(wrap_type(int))
    assert hash(wrap_type(int | str)) == hash(wrap_type(str | int))
    assert hash(wrap_type(list[int | str])) == hash(wrap_type(list[str | int]))
    assert hash(wrap_type(dict[str, int | str])) == hash(wrap_type(dict[str, str | int]))
    assert hash(wrap_type(dict[str, int | str])) != hash(wrap_type(dict[str, int]))
    assert hash(wrap_type(Annotated[int, "test"])) != hash(wrap_type(int))


def test_wrap_cache() -> None:
    assert wrap_type(int) is wrap_type(int)
    assert wrap_type(int | str) is wrap_type(str | int)
    assert wrap_type(list[int | str]) is wrap_type(list[str | int])
    assert wrap_type(dict[str, int | str]) is wrap_type(dict[str, str | int])
    assert wrap_type(dict[str, int | str]) is not wrap_type(dict[str, int])
    assert wrap_type(Annotated[int, "test"]) is not wrap_type(int)


def test_type_bases() -> None:
    class Super:
        pass

    class Type(Super):
        pass

    tw = wrap_type(Type)
    bases = tw[0].bases
    assert len(bases) == 1
    assert bases[0].match(Super)


def test_generic_type_bases() -> None:
    class Super:
        pass

    class Type[T](Super):
        pass

    tw = wrap_type(Type[int])
    bases = tw[0].bases
    assert len(bases) == 1
    assert bases[0].match(Super)


def test_super_generic_type_bases() -> None:
    class Super[T]:
        pass

    class Child[T](Super[str]):
        pass

    tw = wrap_type(Child[int])
    bases = tw[0].bases
    assert len(bases) == 1
    assert bases[0].match(Super[str])


def test_super_transversal_generic_type_bases() -> None:
    class Super[T]:
        pass

    class Child[T](Super[T]):
        pass

    tw = wrap_type(Child[int])
    bases = tw[0].bases
    assert len(bases) == 1
    assert bases[0].match(Super[int])


def test_type_attributes() -> None:
    @dataclass
    class GenericType[T, U]:
        attr1: T
        attr2: U
        attr3: int

    tw = wrap_type(GenericType[int, str])
    attrs = tw.attribute_hints
    assert attrs["attr1"].match(int)
    assert attrs["attr2"].match(str)
    assert attrs["attr3"].match(int)


def test_type_attributes_with_inherited() -> None:
    @dataclass
    class BaseType1[T]:
        base_attr_1: T

    @dataclass
    class BaseType2[T]:
        base_attr_2: T

    @dataclass
    class MidType[T, U](BaseType1[U]):
        mid_attr: T

    @dataclass
    class GenericType[T, U](MidType[U, int], BaseType2[T]):
        attr1: T
        attr2: U

    tw = wrap_type(GenericType[str, bool])
    attrs = tw.attribute_hints
    assert attrs["attr1"].match(str)
    assert attrs["attr2"].match(bool)
    assert attrs["mid_attr"].match(bool)
    assert attrs["base_attr_1"].match(int)
    assert attrs["base_attr_2"].match(str)


def test_type_attributes_no_atomic() -> None:
    t_union = wrap_type(int | str)
    with pytest.raises(TypeError) as info:
        _ = t_union.attribute_hints

    assert info.value.args[0] == "Cannot get attributes of union types"


def test_type_init_signature() -> None:
    class GenericType[T, U]:
        def __init__(self, a: T, b: U) -> None:
            pass

    twrap = wrap_type(GenericType[int, str])
    signature_hints = twrap.init.get_signature_hints()
    assert signature_hints["a"].match(int)
    assert signature_hints["b"].match(str)
    assert signature_hints["return"].match(type(None))


def test_type_method_signature() -> None:
    class GenericType[T, U]:
        def method(self, x: T, y: U) -> bool:
            return True

    twrap = wrap_type(GenericType[int, str])
    fwrap = twrap.get_method("method")

    assert fwrap is not None
    signature_hints = fwrap.get_signature_hints()
    assert signature_hints["x"].match(int)
    assert signature_hints["y"].match(str)
    assert signature_hints["return"].match(bool)
    assert fwrap.get_return_hint().match(bool)


def test_typed_dict_wrap() -> None:
    from typing import TypedDict

    class TestTypedDict(TypedDict, total=False):
        x: int
        y: NotRequired[str]

    twrap = wrap_type(TestTypedDict)
    assert not twrap.total

    attrs = twrap.attribute_hints
    assert attrs["x"].match(int)
    assert attrs["y"].match(str)

    assert attrs["x"].required
    assert not attrs["y"].required


def test_type_signature() -> None:
    class GenericType[T, U]:
        def __init__(self, a: T, b: U) -> None:
            pass

    twrap = wrap_type(GenericType[int, str])
    signature = twrap.signature
    params = [*twrap.parameters.values()]

    assert params[0].name == "a"
    assert params[1].name == "b"
    assert signature.return_annotation is None

    signature = twrap.init.signature
    params = [*twrap.init.parameters.values()]

    assert params[0].name == "self"
    assert params[1].name == "a"
    assert params[2].name == "b"
    assert signature.return_annotation is None


def test_type_instantiate() -> None:
    class GenericType[T, U]:
        def __init__(self, a: T, b: U) -> None:
            self.a = a
            self.b = b

    twrap = wrap_type(GenericType[int, str])
    instance = twrap.instantiate(10, "test")

    assert isinstance(instance, GenericType)
    assert instance.a == 10
    assert instance.b == "test"

    @runtime_checkable
    class WithOrigClass(Protocol):
        __orig_class__: type[Any]

    assert isinstance(instance, WithOrigClass)
    orig_twrap = wrap_type(instance.__orig_class__)
    assert orig_twrap is twrap


def test_fail_type_instantiate_union() -> None:
    t_union = wrap_type(int | str)

    with pytest.raises(TypeError) as info:
        _ = t_union.instantiate()

    assert info.value.args[0] == "Cannot instantiate union types"


def test_get_inner_type() -> None:
    class GenericType[T]:
        pass

    twrap = wrap_type(GenericType[int])

    assert twrap.inner_type is GenericType
    assert twrap.generic_params[0].match(int)


def test_wrap_type_alias() -> None:
    type MyType = dict[str, list[int | str]]  # pyright: ignore[reportGeneralTypeIssues]

    twrap = wrap_type(MyType)

    assert twrap.match(dict)
    assert twrap.generic_params[0].match(str)
    assert twrap.generic_params[1].match(list)
    assert twrap.generic_params[1].generic_params[0].match(int | str)


def test_wrapped_annotated_type() -> None:
    from typing import Annotated

    class GenericType[T]:
        pass

    twrap = wrap_type(Annotated[GenericType[int], "meta"])

    assert twrap.match(GenericType)
    assert twrap.generic_params[0].match(int)
    assert twrap.annotations == ("meta",)


def test_generic_bases() -> None:
    class SuperType[T]: ...

    class SubType[T](SuperType[T]): ...

    assert wrap_type(SubType[int]).nodes[0].bases[0] == wrap_type(SuperType[int])
    assert wrap_type(SubType[str]).nodes[0].bases[0] == wrap_type(SuperType[str])


def test_annotated_type_cached() -> None:
    class SuperType[T]: ...

    @dataclass
    class SubType[T](SuperType[T]):
        parent1: Annotated[SuperType[T], "parent"]
        parent2: Annotated[SuperType[T], "parent"]

    super_twrap = wrap_type(SuperType[int])
    twrap = wrap_type(SubType[int])

    assert twrap.attribute_hints["parent1"].match(super_twrap)

    assert twrap.attribute_hints["parent1"] is not super_twrap
    assert twrap.attribute_hints["parent1"] is twrap.attribute_hints["parent2"]

    assert twrap.attribute_hints["parent1"].annotations == ("parent",)
    assert twrap.attribute_hints["parent2"].annotations == ("parent",)
    assert super_twrap.annotations == ()


def test_generic_attribute_with_union() -> None:
    class ClassA[T]: ...

    class ClassB[T]: ...

    @dataclass
    class ClassC[T, U]:
        attr: ClassA[T] | ClassB[U]

    twrap = wrap_type(ClassC[int, str])

    attr_twrap = twrap.attribute_hints["attr"]
    assert attr_twrap.union
    assert attr_twrap.match(ClassA[int])
    assert attr_twrap.match(ClassB[str])
    assert not attr_twrap.match(ClassA[str])
    assert not attr_twrap.match(ClassB[int])


def test_generic_attribute_with_union_type_alias() -> None:
    class ClassA[T]: ...

    class ClassB[T]: ...

    type ClassAorB[S, R] = ClassA[R] | ClassB[S]  # pyright: ignore[reportGeneralTypeIssues]

    @dataclass
    class ClassC[T, U]:
        attr: ClassAorB[T, U]

    twrap = wrap_type(ClassC[int, str])

    attr_twrap = twrap.attribute_hints["attr"]
    assert attr_twrap.union
    assert attr_twrap.match(ClassA[str])
    assert attr_twrap.match(ClassB[int])
    assert not attr_twrap.match(ClassA[int])
    assert not attr_twrap.match(ClassB[str])


def test_match_super_type_with_generic_params() -> None:
    class SuperType[T]: ...

    class SubType(SuperType[int]): ...

    assert not wrap_type(SubType).match(SuperType[int])
    assert not wrap_type(SubType).match(SuperType[int], match_mode="exact")

    assert wrap_type(SubType).match(SuperType[int], match_mode="super")
    assert not wrap_type(SuperType[int]).match(SubType, match_mode="super")
    assert not wrap_type(SubType).match(SuperType[str], match_mode="super")

    assert wrap_type(SuperType[int]).match(SubType, match_mode="sub")
    assert not wrap_type(SubType).match(SuperType[int], match_mode="sub")
    assert not wrap_type(SuperType[str]).match(SubType, match_mode="sub")

    assert wrap_type(SubType).match(SuperType[int], match_mode="any")
    assert wrap_type(SuperType[int]).match(SubType, match_mode="any")
    assert not wrap_type(SubType).match(SuperType[str], match_mode="any")
    assert not wrap_type(SuperType[str]).match(SubType, match_mode="any")

    assert wrap_type(SubType).match(SuperType[int | str], match_mode="super")
    assert wrap_type(SubType).match(SuperType[Any], match_mode="super")


def test_match_super_generic_type_with_generic_params() -> None:
    class SuperType[T]: ...

    class SubType[T](SuperType[T]): ...

    assert not wrap_type(SubType[int]).match(SuperType[int])
    assert not wrap_type(SubType[int]).match(SuperType[int], match_mode="exact")

    assert wrap_type(SubType[int]).match(SuperType[int], match_mode="super")
    assert not wrap_type(SuperType[int]).match(SubType[int], match_mode="super")
    assert not wrap_type(SubType[str]).match(SuperType[int], match_mode="super")

    assert wrap_type(SuperType[int]).match(SubType[int], match_mode="sub")
    assert not wrap_type(SubType[int]).match(SuperType[int], match_mode="sub")
    assert not wrap_type(SuperType[int]).match(SubType[str], match_mode="sub")

    assert wrap_type(SubType[int]).match(SuperType[int], match_mode="any")
    assert wrap_type(SuperType[int]).match(SubType[int], match_mode="any")
    assert not wrap_type(SubType[str]).match(SuperType[int], match_mode="any")
    assert not wrap_type(SuperType[str]).match(SubType[int], match_mode="any")

    assert wrap_type(SubType[int]).match(SuperType[int | str], match_mode="super")
    assert wrap_type(SubType[int]).match(SuperType[Any], match_mode="super")


def test_obj_instance_of_builtin() -> None:
    assert wrap_type(int).is_type_of(5)
    assert not wrap_type(int).is_type_of("test")
    assert wrap_type(int).is_type_of(True)


def test_obj_instance_of_union() -> None:
    assert wrap_type(int | str).is_type_of(5)
    assert wrap_type(int | str).is_type_of("test")
    assert not wrap_type(int | str).is_type_of(3.14)


def test_obj_instance_of_generic() -> None:
    class GenericType[T]:
        pass

    assert wrap_type(GenericType[int]).is_type_of(GenericType[int]())
    assert not wrap_type(GenericType[int]).is_type_of(GenericType[str]())


def test_obj_instance_of_generic_parent() -> None:
    class GenericType[T]:
        pass

    class SubType(GenericType[int]):
        pass

    assert wrap_type(SubType).is_type_of(SubType())
    assert wrap_type(GenericType[int]).is_type_of(SubType())


def test_obj_generic_instance_of_generic_parent() -> None:
    class GenericType[T]:
        pass

    class SubType[T, U](GenericType[U]):
        pass

    assert wrap_type(SubType[str, int]).is_type_of(SubType[str, int]())
    assert wrap_type(GenericType[int]).is_type_of(SubType[str, int]())

    assert not wrap_type(SubType[int, str]).is_type_of(SubType[int, int]())
    assert not wrap_type(GenericType[str]).is_type_of(SubType[int, int]())


def test_specialize_twrap() -> None:
    class GenericType[T]:
        pass

    class SubType[T](GenericType[T]):
        pass

    super_any = wrap_type(GenericType[Any])
    sub_int = wrap_type(SubType[int])

    super_int = super_any.specialize_with(sub_int)
    assert super_int is wrap_type(GenericType[int])
    assert super_int is not wrap_type(GenericType[str])
    assert super_int.origin == GenericType[int]
    assert super_int.origin != GenericType[str]


def test_reverse_specialize_twrap() -> None:
    class GenericType[T]:
        pass

    class SubType[T](GenericType[T]):
        pass

    super_int = wrap_type(GenericType[int])
    sub_any = wrap_type(SubType[Any])

    sub_int = sub_any.specialize_with(super_int)
    assert sub_int is wrap_type(SubType[int])
    assert sub_int is not wrap_type(SubType[str])
    assert sub_int.origin == SubType[int]
    assert sub_int.origin != SubType[str]


def test_specialize_twrap_three_levels() -> None:
    class GenericType[A]:
        pass

    class SubType[B](GenericType[B]):
        pass

    class SubsubType[C](SubType[C]):
        pass

    super_any = wrap_type(GenericType[Any])
    subsub_int = wrap_type(SubsubType[int])

    assert super_any.specialize_with(subsub_int) is wrap_type(GenericType[int])


def test_reverse_specialize_twrap_three_levels() -> None:
    class GenericType[A]:
        pass

    class SubType[B](GenericType[B]):
        pass

    class SubsubType[C](SubType[C]):
        pass

    super_int = wrap_type(GenericType[int])
    subsub_any = wrap_type(SubsubType[Any])

    assert subsub_any.specialize_with(super_int) is wrap_type(SubsubType[int])


def test_specialize_twrap_four_levels() -> None:
    class GenericType[A]:
        pass

    class SubType[B](GenericType[B]):
        pass

    class SubsubType[C](SubType[C]):
        pass

    class SubsubsubType[D](SubsubType[D]):
        pass

    super_any = wrap_type(GenericType[Any])
    subsubsub_int = wrap_type(SubsubsubType[int])

    assert super_any.specialize_with(subsubsub_int) is wrap_type(GenericType[int])


def test_reverse_specialize_twrap_four_levels() -> None:
    class GenericType[A]:
        pass

    class SubType[B](GenericType[B]):
        pass

    class SubsubType[C](SubType[C]):
        pass

    class SubsubsubType[D](SubsubType[D]):
        pass

    super_int = wrap_type(GenericType[int])
    subsubsub_any = wrap_type(SubsubsubType[Any])

    assert subsubsub_any.specialize_with(super_int) is wrap_type(SubsubsubType[int])


def test_specialize_twrap_fork() -> None:
    class GenericParent1[A1]:
        pass

    class GenericParent2[A2]:
        pass

    class SubType[B1, B2](GenericParent1[B1], GenericParent2[B2]):
        pass

    class SubsubType[C1, C2](SubType[C1, C2]):
        pass

    super1_any = wrap_type(GenericParent1[Any])
    super2_any = wrap_type(GenericParent2[Any])
    subsub_int_str = wrap_type(SubsubType[int, str])

    assert super1_any.specialize_with(subsub_int_str) is wrap_type(GenericParent1[int])
    assert super2_any.specialize_with(subsub_int_str) is wrap_type(GenericParent2[str])


def test_reverse_partial_specialize_twrap_fork() -> None:
    class GenericParent1[A1]:
        pass

    class GenericParent2[A2]:
        pass

    class SubType[B1, B2](GenericParent1[B1], GenericParent2[B2]):
        pass

    class SubsubType[C1, C2](SubType[C1, C2]):
        pass

    super1_int = wrap_type(GenericParent1[int])
    super2_str = wrap_type(GenericParent2[str])
    subsub_any_any = wrap_type(SubsubType[Any, Any])

    assert subsub_any_any.specialize_with(super1_int) is wrap_type(SubsubType[int, Any])
    assert subsub_any_any.specialize_with(super2_str) is wrap_type(SubsubType[Any, str])


def test_fail_specialize_twrap_no_match() -> None:
    class GenericType[T]:
        pass

    class OtherType[T]:
        pass

    super_any = wrap_type(GenericType[Any])
    other_int = wrap_type(OtherType[int])

    with pytest.raises(IncompatibleTypesError) as exc_info:
        super_any.specialize_with(other_int)

    assert exc_info.value.c1 is GenericType[Any]
    assert exc_info.value.c2 is OtherType[int]
