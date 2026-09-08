from typing import Any

import pytest

from peritype import wrap_type
from peritype.collections import TypeBag


def test_type_bag() -> None:
    bag = TypeBag()

    class TestType: ...

    twrap = wrap_type(TestType)
    bag.add(twrap)

    assert twrap in bag
    assert bag.contains_matching(twrap)
    assert bag.first_matching(twrap) == twrap
    assert bag.get_all_matching(twrap) == {twrap}


def test_type_bag_generic() -> None:
    bag = TypeBag()

    class TestType[T]: ...

    bag.add(wrap_type(TestType[int]))
    bag.add(wrap_type(TestType[str]))

    assert bag.get_all_matching(wrap_type(TestType[int])) == {wrap_type(TestType[int])}
    assert bag.get_all_matching(wrap_type(TestType[str])) == {wrap_type(TestType[str])}
    assert bag.get_all_matching(wrap_type(TestType[Any])) == {
        wrap_type(TestType[int]),
        wrap_type(TestType[str]),
    }


def test_get_all_subtypes() -> None:
    bag = TypeBag()

    class BaseType: ...

    class SubTypeA(BaseType): ...

    class SubTypeB(BaseType): ...

    bag.add(wrap_type(SubTypeA))
    bag.add(wrap_type(SubTypeB))

    assert bag.get_all_submatching(wrap_type(BaseType)) == {
        wrap_type(SubTypeA),
        wrap_type(SubTypeB),
    }


def test_get_all_subtypes_generic() -> None:
    bag = TypeBag()

    class BaseType[T]: ...

    class SubTypeA(BaseType[int]): ...

    class SubTypeB(BaseType[str]): ...

    bag.add(wrap_type(SubTypeA))
    bag.add(wrap_type(SubTypeB))

    assert bag.get_all_submatching(wrap_type(BaseType[Any])) == {
        wrap_type(SubTypeA),
        wrap_type(SubTypeB),
    }
    assert bag.get_all_submatching(wrap_type(BaseType[int])) == {
        wrap_type(SubTypeA),
    }
    assert bag.get_all_submatching(wrap_type(BaseType[str])) == {
        wrap_type(SubTypeB),
    }
    assert bag.get_all_submatching(wrap_type(BaseType[float])) == set()


def test_match_not_fully_defined() -> None:
    bag = TypeBag()

    class TestType[T]: ...

    twrap_int = wrap_type(TestType[int])
    twrap_any = wrap_type(TestType[Any])

    bag.add(twrap_any)

    assert twrap_any in bag
    assert twrap_int not in bag
    assert bag.contains_matching(twrap_int)
    assert bag.first_matching(twrap_int) == twrap_any


def test_match_union() -> None:
    bag = TypeBag()

    class TestType[T]: ...

    twrap_int = wrap_type(TestType[int])
    twrap_union = wrap_type(TestType[int | str])

    bag.add(twrap_union)

    assert twrap_union in bag
    assert twrap_int not in bag
    assert bag.contains_matching(twrap_int)
    assert bag.first_matching(twrap_int) == twrap_union


def test_match_none() -> None:
    bag = TypeBag()

    class TestType[T]: ...

    twrap_int = wrap_type(TestType[int])
    twrap_str = wrap_type(TestType[str])

    bag.add(twrap_int)

    assert twrap_int in bag
    assert not bag.contains_matching(twrap_str)
    assert bag.first_matching_or_none(twrap_str) is None

    with pytest.raises(KeyError):
        bag.first_matching(twrap_str)


def test_remove() -> None:
    bag = TypeBag()

    class TestType[T]: ...

    twrap_int = wrap_type(TestType[int])
    twrap_str = wrap_type(TestType[str])

    bag.add(twrap_int)
    bag.add(twrap_str)

    assert len(bag) == 2

    bag.remove(twrap_int)

    assert len(bag) == 1
    assert twrap_int not in bag
    assert twrap_str in bag

    bag.remove(twrap_str)
    assert len(bag) == 0


def test_iter() -> None:
    bag = TypeBag()

    class TestType[T]: ...

    twrap_int = wrap_type(TestType[int])
    twrap_str = wrap_type(TestType[str])

    bag.add(twrap_int)
    bag.add(twrap_str)

    items: set[Any] = set()
    for item in bag:
        items.add(item)
    assert items == {twrap_int, twrap_str}

    assert bag.items() == {twrap_int, twrap_str}


def test_copy() -> None:
    bag = TypeBag()

    class TestType[T]: ...

    twrap_int = wrap_type(TestType[int])
    twrap_str = wrap_type(TestType[str])
    twrap_float = wrap_type(TestType[float])

    bag.add(twrap_int)
    bag.add(twrap_str)

    assert len(bag) == 2

    bag_copy = bag.copy()

    assert len(bag_copy) == 2
    assert twrap_int in bag_copy
    assert twrap_str in bag_copy

    bag_copy.add(twrap_float)

    assert len(bag) == 2
    assert len(bag_copy) == 3
    assert twrap_float not in bag
    assert twrap_float in bag_copy


def test_typed_type_bag() -> None:
    b1 = TypeBag[int]()

    b1.add(wrap_type(int))
    assert wrap_type(int) in b1
    assert wrap_type(bool) not in b1

    b1.add(wrap_type(bool))
    assert wrap_type(int) in b1
    assert wrap_type(bool) in b1

    # pyright SHOULD report that usage
    b1.add(wrap_type(str))  # pyright: ignore[reportArgumentType]
