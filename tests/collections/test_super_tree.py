from typing import Any

from peritype import wrap_type
from peritype.collections import TypeSuperTree


def test_simple_type_in_super_tree() -> None:
    tree = TypeSuperTree()

    class SuperType: ...

    class SubType(SuperType): ...

    super_twrap = wrap_type(SuperType)
    twrap = wrap_type(SubType)
    tree.add(twrap)

    assert wrap_type(SuperType) in tree
    assert tree[wrap_type(SuperType)] == {twrap, super_twrap}
    assert wrap_type(SubType) in tree
    assert tree[wrap_type(SubType)] == {twrap}


def test_generic_type_in_super_tree() -> None:
    tree = TypeSuperTree()

    from typing import Generic, TypeVar

    T = TypeVar("T")

    class SuperType(Generic[T]): ...

    class SubType(SuperType[int]): ...

    super_twrap = wrap_type(SuperType[int])
    twrap = wrap_type(SubType)
    tree.add(twrap)

    assert wrap_type(SuperType[int]) in tree
    assert tree[wrap_type(SuperType[int])] == {twrap, super_twrap}
    assert wrap_type(SubType) in tree
    assert tree[wrap_type(SubType)] == {twrap}

    assert wrap_type(SuperType) not in tree
    assert wrap_type(SuperType[str]) not in tree


def test_multiple_inheritance_in_super_tree() -> None:
    tree = TypeSuperTree()

    class SuperType[T]: ...

    class MidType[T](SuperType[T]): ...

    class SubType[T](MidType[T]): ...

    super_twrap = wrap_type(SuperType[int])
    mid_twrap = wrap_type(MidType[int])
    twrap = wrap_type(SubType[int])
    tree.add(twrap)

    assert wrap_type(SuperType[int]) in tree
    assert tree[wrap_type(SuperType[int])] == {twrap, mid_twrap, super_twrap}
    assert wrap_type(MidType[int]) in tree
    assert tree[wrap_type(MidType[int])] == {twrap, mid_twrap}
    assert wrap_type(SubType[int]) in tree
    assert tree[wrap_type(SubType[int])] == {twrap}

    assert wrap_type(SuperType) not in tree
    assert wrap_type(SuperType[str]) not in tree
    assert wrap_type(MidType) not in tree
    assert wrap_type(MidType[str]) not in tree


def test_not_fully_defined_not_in_super_tree() -> None:
    tree = TypeSuperTree()

    class TestType[T]: ...

    tree.add(wrap_type(TestType[int]))

    assert wrap_type(TestType[int]) in tree
    assert wrap_type(TestType[Any]) not in tree
