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

    assert super_twrap in tree
    assert tree[super_twrap] == {twrap}
    assert twrap in tree
    assert tree[twrap] == {twrap}


def test_generic_type_in_super_tree() -> None:
    tree = TypeSuperTree()

    from typing import Generic, TypeVar

    T = TypeVar("T")

    class SuperType(Generic[T]): ...

    class SubType(SuperType[int]): ...

    super_twrap = wrap_type(SuperType[int])
    twrap = wrap_type(SubType)
    tree.add(twrap)

    assert super_twrap in tree
    assert tree[super_twrap] == {twrap}
    assert twrap in tree
    assert tree[twrap] == {twrap}

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

    assert super_twrap in tree
    assert tree[super_twrap] == {twrap}
    assert mid_twrap in tree
    assert tree[mid_twrap] == {twrap}
    assert twrap in tree
    assert tree[twrap] == {twrap}

    assert wrap_type(SuperType) not in tree
    assert wrap_type(SuperType[str]) not in tree
    assert wrap_type(MidType) not in tree
    assert wrap_type(MidType[str]) not in tree


def test_sister_classes_in_tree() -> None:
    tree = TypeSuperTree()

    class SuperType: ...

    class SubType1(SuperType): ...

    class SubType2(SuperType): ...

    super_twrap = wrap_type(SuperType)
    twrap1 = wrap_type(SubType1)
    twrap2 = wrap_type(SubType2)
    tree.add(twrap1)
    tree.add(twrap2)

    assert super_twrap in tree
    assert tree[super_twrap] == {twrap1, twrap2}
    assert twrap1 in tree
    assert tree[twrap1] == {twrap1}
    assert twrap2 in tree
    assert tree[twrap2] == {twrap2}


def test_generic_sister_classes_in_tree() -> None:
    tree = TypeSuperTree()

    class SuperType[T]: ...

    class SubType1(SuperType[int]): ...

    class SubType2[T](SuperType[T]): ...

    super_twrap_int = wrap_type(SuperType[int])
    super_twrap_str = wrap_type(SuperType[str])
    twrap1 = wrap_type(SubType1)
    twrap2 = wrap_type(SubType2[int])
    twrap3 = wrap_type(SubType2[str])
    tree.add(twrap1)
    tree.add(twrap2)
    tree.add(twrap3)

    assert super_twrap_int in tree
    assert tree[super_twrap_int] == {twrap1, twrap2}
    assert super_twrap_str in tree
    assert tree[super_twrap_str] == {twrap3}
    assert twrap1 in tree
    assert tree[twrap1] == {twrap1}
    assert twrap2 in tree
    assert tree[twrap2] == {twrap2}


def test_not_fully_defined_not_in_super_tree() -> None:
    tree = TypeSuperTree()

    class TestType[T]: ...

    tree.add(wrap_type(TestType[int]))

    assert wrap_type(TestType[int]) in tree
    assert wrap_type(TestType[Any]) not in tree
