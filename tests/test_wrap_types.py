from collections.abc import Coroutine
from typing import Annotated, Any, Concatenate, Generic, get_origin

from peritype import TWrap, wrap_type


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
    assert t_union.is_union
    assert not t_union.is_nullable

    t_nullable = wrap_type(int | None)
    assert isinstance(t_nullable, TWrap)
    assert not t_nullable.is_union
    assert t_nullable.is_nullable


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
    assert len(bases) == 2
    assert bases[0].match(Super)
    assert get_origin(bases[1].origin) is Generic


def test_super_generic_type_bases() -> None:
    class Super[T]:
        pass

    class Child[T](Super[str]):
        pass

    tw = wrap_type(Child[int])
    bases = tw[0].bases
    assert len(bases) == 2
    assert bases[0].match(Super[str])
    assert get_origin(bases[1].origin) is Generic


def test_super_transversal_generic_type_bases() -> None:
    class Super[T]:
        pass

    class Child[T](Super[T]):
        pass

    tw = wrap_type(Child[int])
    bases = tw[0].bases
    assert len(bases) == 2
    assert bases[0].match(Super[int])
    assert get_origin(bases[1].origin) is Generic
