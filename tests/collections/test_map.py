from peritype import wrap_type
from peritype.collections import TypeMap


def test_type_map() -> None:
    map = TypeMap()

    class TestType:
        pass

    map.push(wrap_type(TestType), 1)

    assert wrap_type(TestType) in map
    assert map[wrap_type(TestType)] == {1}

    collection = map.get(wrap_type(TestType), hint=int, not_none=True)
    assert collection == {1}


def test_type_map_generic() -> None:
    map = TypeMap()

    class TestType[T]:
        pass

    map.push(wrap_type(TestType[int]), 1)

    assert wrap_type(TestType[int]) in map
    assert map[wrap_type(TestType[int])] == {1}

    assert wrap_type(TestType[str]) not in map
