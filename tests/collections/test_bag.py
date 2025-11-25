from typing import Any

from peritype.collections import TypeBag
from peritype.wrap import wrap_type


def test_type_bag() -> None:
    bag = TypeBag()

    class TestType: ...

    twrap = wrap_type(TestType)
    bag.add(twrap)

    assert twrap in bag
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
