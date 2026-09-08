"""``TypeMap`` and ``TypeSetMap``: dictionaries keyed by wraps."""

from typing import Any

import pytest

from peritype import wrap_type
from peritype.collections import TypeMap, TypeSetMap


@pytest.fixture
def type_map() -> TypeMap[Any, str]:
    type_map = TypeMap[Any, str]()
    type_map[wrap_type(int)] = "int"
    type_map[wrap_type(list[str])] = "list"
    return type_map


class TestTypeMap:
    def test_set_get_contains_len(self, type_map: TypeMap[Any, str]) -> None:
        assert type_map[wrap_type(int)] == "int"
        assert wrap_type(int) in type_map
        assert wrap_type(str) not in type_map
        assert len(type_map) == 2

    def test_missing_key_raises(self, type_map: TypeMap[Any, str]) -> None:
        with pytest.raises(KeyError):
            type_map[wrap_type(str)]

    def test_get_with_default(self, type_map: TypeMap[Any, str]) -> None:
        assert type_map.get(wrap_type(int)) == "int"
        assert type_map.get(wrap_type(str)) is None
        assert type_map.get(wrap_type(str), default="fallback") == "fallback"

    def test_add_is_an_alias_for_setitem(self, type_map: TypeMap[Any, str]) -> None:
        type_map.add(wrap_type(float), "float")
        assert type_map[wrap_type(float)] == "float"

    def test_overwrite(self, type_map: TypeMap[Any, str]) -> None:
        type_map[wrap_type(int)] = "integer"
        assert type_map[wrap_type(int)] == "integer"
        assert len(type_map) == 2

    def test_delete(self, type_map: TypeMap[Any, str]) -> None:
        del type_map[wrap_type(int)]
        assert wrap_type(int) not in type_map
        with pytest.raises(KeyError):
            del type_map[wrap_type(int)]

    def test_equal_wraps_are_the_same_key(self, type_map: TypeMap[Any, str]) -> None:
        type_map[wrap_type(int | None)] = "optional"
        assert type_map[wrap_type(None | int)] == "optional"
        assert len(type_map) == 3

    def test_views(self, type_map: TypeMap[Any, str]) -> None:
        assert type_map.items() == {wrap_type(int): "int", wrap_type(list[str]): "list"}
        assert set(type_map.keys()) == {wrap_type(int), wrap_type(list[str])}
        assert sorted(type_map.values()) == ["int", "list"]

    def test_items_is_a_copy(self, type_map: TypeMap[Any, str]) -> None:
        type_map.items()[wrap_type(str)] = "str"
        assert wrap_type(str) not in type_map

    def test_copy_is_independent(self, type_map: TypeMap[Any, str]) -> None:
        copy = type_map.copy()
        copy[wrap_type(str)] = "str"
        del copy[wrap_type(int)]
        assert wrap_type(str) not in type_map
        assert wrap_type(int) in type_map
        assert copy[wrap_type(str)] == "str"


class TestTypeSetMap:
    def test_push_creates_the_set(self) -> None:
        set_map = TypeSetMap[Any, str]()
        set_map.push(wrap_type(int), "a")
        set_map.push(wrap_type(int), "b")
        set_map.push(wrap_type(int), "a")
        assert set_map[wrap_type(int)] == {"a", "b"}
        assert set_map.count(wrap_type(int)) == 2

    def test_count_of_a_missing_key_is_zero(self) -> None:
        set_map = TypeSetMap[Any, str]()
        assert set_map.count(wrap_type(int)) == 0
        assert wrap_type(int) not in set_map

    def test_copy_keeps_the_subclass(self) -> None:
        set_map = TypeSetMap[Any, str]()
        set_map.push(wrap_type(int), "a")
        copy = set_map.copy()
        copy.push(wrap_type(int), "b")
        assert set_map.count(wrap_type(int)) == 1
        assert copy.count(wrap_type(int)) == 2

    def test_is_a_type_map(self) -> None:
        set_map = TypeSetMap[Any, str]()
        set_map[wrap_type(int)] = {"a"}
        assert isinstance(set_map, TypeMap)
        assert set_map.get(wrap_type(int)) == {"a"}
