"""``TypeSuperTree``: indexing wraps by every type they derive from."""

from typing import Any

import pytest

from peritype import wrap_type
from peritype.collections import TypeSuperTree


class Root: ...


class Mid(Root): ...


class Leaf(Mid): ...


class Other: ...


class Diamond(Mid, Other): ...


class GRoot[T]: ...


class GMid[T](GRoot[T]): ...


class GLeaf[T](GMid[T]): ...


class FixedMid(GRoot[int]): ...


class FixedLeaf(FixedMid): ...


class TestAdd:
    def test_registers_the_type_and_its_direct_base(self) -> None:
        tree = TypeSuperTree()
        tree.add(wrap_type(Mid))
        assert tree[wrap_type(Mid)] == {wrap_type(Mid)}
        assert tree[wrap_type(Root)] == {wrap_type(Mid)}

    def test_object_is_never_a_key(self) -> None:
        tree = TypeSuperTree()
        tree.add(wrap_type(Mid))
        assert wrap_type(object) not in tree

    def test_walks_the_whole_hierarchy(self) -> None:
        tree = TypeSuperTree()
        tree.add(wrap_type(Leaf))
        assert tree[wrap_type(Root)] == {wrap_type(Leaf)}
        assert tree[wrap_type(Mid)] == {wrap_type(Leaf)}
        assert tree[wrap_type(Leaf)] == {wrap_type(Leaf)}

    def test_several_types_accumulate_under_a_shared_base(self) -> None:
        tree = TypeSuperTree()
        tree.add(wrap_type(Mid))
        tree.add(wrap_type(Leaf))
        assert tree[wrap_type(Root)] == {wrap_type(Mid), wrap_type(Leaf)}
        assert tree[wrap_type(Mid)] == {wrap_type(Mid), wrap_type(Leaf)}

    def test_multiple_inheritance_registers_every_base(self) -> None:
        tree = TypeSuperTree()
        tree.add(wrap_type(Diamond))
        assert tree[wrap_type(Mid)] == {wrap_type(Diamond)}
        assert tree[wrap_type(Root)] == {wrap_type(Diamond)}
        assert tree[wrap_type(Other)] == {wrap_type(Diamond)}

    def test_generic_bases_keep_their_parameters(self) -> None:
        tree = TypeSuperTree()
        tree.add(wrap_type(FixedMid))
        assert wrap_type(GRoot[int]) in tree
        assert wrap_type(GRoot[str]) not in tree
        assert wrap_type(GRoot[Any]) not in tree
        assert tree[wrap_type(GRoot[int])] == {wrap_type(FixedMid)}

    def test_generic_chain(self) -> None:
        tree = TypeSuperTree()
        tree.add(wrap_type(GLeaf[int]))
        assert tree[wrap_type(GMid[int])] == {wrap_type(GLeaf[int])}
        assert tree[wrap_type(GRoot[int])] == {wrap_type(GLeaf[int])}
        assert wrap_type(GRoot[str]) not in tree

    def test_plain_subclass_of_generic_derived_class(self) -> None:
        tree = TypeSuperTree()
        tree.add(wrap_type(FixedLeaf))
        assert wrap_type(FixedMid) in tree
        assert tree[wrap_type(FixedMid)] == {wrap_type(FixedLeaf)}
        assert tree[wrap_type(GRoot[int])] == {wrap_type(FixedLeaf)}


class TestMappingBehaviour:
    def test_missing_key_raises(self) -> None:
        tree = TypeSuperTree()
        assert wrap_type(Root) not in tree
        with pytest.raises(KeyError):
            tree[wrap_type(Root)]

    def test_delete(self) -> None:
        tree = TypeSuperTree()
        tree.add(wrap_type(Mid))
        del tree[wrap_type(Root)]
        assert wrap_type(Root) not in tree
        assert wrap_type(Mid) in tree

    def test_copy_is_independent(self) -> None:
        tree = TypeSuperTree()
        tree.add(wrap_type(Mid))
        copy = tree.copy()
        copy.add(wrap_type(Other))
        del copy[wrap_type(Root)]
        assert wrap_type(Other) not in tree
        assert wrap_type(Root) in tree
        assert wrap_type(Other) in copy
