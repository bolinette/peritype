from typing import Any

from peritype import wrap_type
from peritype.collections import TypeMap, TypeSetMap


def test_type_map() -> None:
    map = TypeMap[Any, int]()

    class TestType:
        pass

    map.add(wrap_type(TestType), 1)

    assert wrap_type(TestType) in map
    assert map[wrap_type(TestType)] == 1

    assert len(map) == 1

    value = map.get(wrap_type(TestType))
    assert value == 1

    value = map.get(wrap_type(int))
    assert value is None

    value = map.get(wrap_type(int), default=42)
    assert value == 42

    del map[wrap_type(TestType)]
    assert wrap_type(TestType) not in map


def test_type_map_generic() -> None:
    map = TypeMap[Any, int]()

    class TestType[T]:
        pass

    map[wrap_type(TestType[int])] = 1

    assert wrap_type(TestType[int]) in map
    assert map[wrap_type(TestType[int])] == 1

    assert wrap_type(TestType[str]) not in map


def test_type_set_map() -> None:
    map = TypeSetMap[Any, int]()

    class TestType:
        pass

    map.push(wrap_type(TestType), 1)
    map.push(wrap_type(TestType), 2)

    assert len(map) == 1
    assert map.count(wrap_type(TestType)) == 2
    assert map.count(wrap_type(int)) == 0

    assert wrap_type(TestType) in map
    assert map.count(wrap_type(TestType)) == 2
    assert map[wrap_type(TestType)] == {1, 2}

    value = map.get(wrap_type(int))
    assert value is None
