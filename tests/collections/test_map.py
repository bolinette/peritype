from typing import Any

from peritype import TWrap, wrap_type
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


def test_iter_items() -> None:
    map = TypeMap[Any, int]()

    class TestTypeA:
        pass

    class TestTypeB:
        pass

    map.add(wrap_type(TestTypeA), 1)
    map.add(wrap_type(TestTypeB), 2)

    items: set[tuple[TWrap[Any], int]] = set()
    for key, value in map:
        items.add((key, value))
    assert items == {(wrap_type(TestTypeA), 1), (wrap_type(TestTypeB), 2)}

    assert map.items() == {wrap_type(TestTypeA): 1, wrap_type(TestTypeB): 2}

    assert {*map.keys()} == {wrap_type(TestTypeA), wrap_type(TestTypeB)}
    assert {*map.values()} == {1, 2}


def test_copy() -> None:
    map = TypeMap[Any, int]()

    class TestTypeA:
        pass

    class TestTypeB:
        pass

    class TestTypeC:
        pass

    map.add(wrap_type(TestTypeA), 1)
    map.add(wrap_type(TestTypeB), 2)

    map_copy = map.copy()

    assert len(map_copy) == 2
    assert map_copy[wrap_type(TestTypeA)] == 1
    assert map_copy[wrap_type(TestTypeB)] == 2

    map_copy.add(wrap_type(TestTypeC), 3)

    assert len(map) == 2
    assert len(map_copy) == 3
    assert wrap_type(TestTypeC) not in map
    assert wrap_type(TestTypeC) in map_copy
