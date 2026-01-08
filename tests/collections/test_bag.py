from typing import Any

from peritype.collections import TypeBag
from peritype.wrap import wrap_type


def test_type_bag() -> None:
    bag = TypeBag()

    class TestType: ...

    twrap = wrap_type(TestType)
    bag.add(twrap)

    assert twrap in bag
    assert bag.contains_matching(twrap)
    assert bag.get_matching(twrap) == twrap
    assert bag.get_all(twrap) == {twrap}


def test_type_bag_generic() -> None:
    bag = TypeBag()

    class TestType[T]: ...

    bag.add(wrap_type(TestType[int]))
    bag.add(wrap_type(TestType[str]))

    assert bag.get_all(wrap_type(TestType[int])) == {wrap_type(TestType[int])}
    assert bag.get_all(wrap_type(TestType[str])) == {wrap_type(TestType[str])}
    assert bag.get_all(wrap_type(TestType[Any])) == {
        wrap_type(TestType[int]),
        wrap_type(TestType[str]),
    }


def test_match_not_fully_defined() -> None:
    bag = TypeBag()

    class TestType[T]: ...

    twrap_int = wrap_type(TestType[int])
    twrap_any = wrap_type(TestType[Any])

    bag.add(twrap_any)

    assert twrap_any in bag
    assert twrap_int not in bag
    assert bag.contains_matching(twrap_int)
    assert bag.get_matching(twrap_int) == twrap_any


def test_match_union() -> None:
    bag = TypeBag()

    class TestType[T]: ...

    twrap_int = wrap_type(TestType[int])
    twrap_union = wrap_type(TestType[int | str])

    bag.add(twrap_union)

    assert twrap_union in bag
    assert twrap_int not in bag
    assert bag.contains_matching(twrap_int)
    assert bag.get_matching(twrap_int) == twrap_union
