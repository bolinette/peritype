from typing import Annotated, Any

import pytest

from peritype import FWrap, wrap_func, wrap_type
from peritype.errors import UnresolvedFunctionTypeVarsError, UnresolvedTypeVarError


def test_wrap_basic_func() -> None:
    def func(x: int, y: str) -> bool: ...

    fwrap = wrap_func(func)
    assert isinstance(fwrap, FWrap)
    assert not fwrap.is_generic
    assert fwrap.is_defined

    parameters = fwrap.parameters
    assert "x" in parameters
    assert "y" in parameters
    assert fwrap.param_at(0).annotation is int
    assert fwrap.param_at(1).annotation is str
    assert fwrap.get_signature_hint(0).match(int)
    assert fwrap.get_signature_hint(1).match(str)

    signature_hints = fwrap.get_signature_hints()
    assert signature_hints["x"].match(int)
    assert signature_hints["y"].match(str)
    assert signature_hints["return"].match(bool)
    assert fwrap.get_return_hint().match(bool)


def test_wrap_init_with_typevar() -> None:
    class TestType[T]:
        def __init__(self, value: T) -> None: ...

    twrap = wrap_type(TestType[int])
    fwrap = wrap_func(getattr(TestType, "__init__"))  # noqa: B009

    signature_hints = fwrap.get_signature_hints(belongs_to=twrap)
    assert signature_hints["value"].match(int)
    assert signature_hints["return"].match(None)


def test_wrap_init_with_typevar_in_super() -> None:
    class SuperSuper[T]:
        def __init__(self, value: T) -> None: ...

    class Super[T](SuperSuper[float]):
        def __init__(self, value: T) -> None: ...

    class TestType[T](Super[int]):
        def __init__(self, value: T) -> None: ...

    twrap = wrap_type(TestType[bool])
    fwrap_child = wrap_func(getattr(TestType, "__init__"))  # noqa: B009
    fwrap_super = wrap_func(getattr(Super, "__init__"))  # noqa: B009
    fwrap_super_super = wrap_func(getattr(SuperSuper, "__init__"))  # noqa: B009

    signature_hints = fwrap_child.get_signature_hints(belongs_to=twrap)
    assert signature_hints["value"].match(bool)
    assert signature_hints["return"].match(None)
    signature_hints = fwrap_super.get_signature_hints(belongs_to=twrap)
    assert signature_hints["value"].match(int)
    assert signature_hints["return"].match(None)
    signature_hints = fwrap_super_super.get_signature_hints(belongs_to=twrap)
    assert signature_hints["value"].match(float)
    assert signature_hints["return"].match(None)


def test_wrap_init_with_transversal_typevar_in_super() -> None:
    class P1: ...

    class P2: ...

    class P3: ...

    class SuperSuper[T]:
        def __init__(self, value: T) -> None: ...

    class Super[T, U](SuperSuper[U]):
        def __init__(self, value: T) -> None: ...

    class TestType[T, U, V](Super[U, V]):
        def __init__(self, value: T) -> None: ...

    twrap = wrap_type(TestType[P1, P2, P3])
    fwrap_child = wrap_func(getattr(TestType, "__init__"))  # noqa: B009
    fwrap_super = wrap_func(getattr(Super, "__init__"))  # noqa: B009
    fwrap_super_super = wrap_func(getattr(SuperSuper, "__init__"))  # noqa: B009

    signature_hints = fwrap_child.get_signature_hints(belongs_to=twrap)
    assert signature_hints["value"].match(P1)
    assert signature_hints["return"].match(None)
    signature_hints = fwrap_super.get_signature_hints(belongs_to=twrap)
    assert signature_hints["value"].match(P2)
    assert signature_hints["return"].match(None)
    signature_hints = fwrap_super_super.get_signature_hints(belongs_to=twrap)
    assert signature_hints["value"].match(P3)
    assert signature_hints["return"].match(None)


def test_wrap_init_with_union() -> None:
    class P1: ...

    class P2: ...

    class TestType1[T]:
        def __init__(self, value: T) -> None: ...

    class TestType2[T]:
        def __init__(self, value: T) -> None: ...

    twrap = wrap_type(TestType1[P1] | TestType2[P2])
    fwrap1 = wrap_func(getattr(TestType1, "__init__"))  # noqa: B009
    fwrap2 = wrap_func(getattr(TestType2, "__init__"))  # noqa: B009

    signature_hints = fwrap1.get_signature_hints(belongs_to=twrap)
    assert signature_hints["value"].match(P1)
    assert signature_hints["return"].match(None)

    signature_hints = fwrap2.get_signature_hints(belongs_to=twrap)
    assert signature_hints["value"].match(P2)
    assert signature_hints["return"].match(None)


def test_wrap_specialize_generic_function() -> None:
    def generic_func[T](x: T) -> T: ...

    fwrap = wrap_func(generic_func)

    with pytest.raises(UnresolvedTypeVarError):
        fwrap.get_signature_hints()
    assert fwrap.is_generic
    assert not fwrap.is_defined

    spe_fwrap = fwrap.specialize((wrap_type(int),))
    assert spe_fwrap.is_generic
    assert spe_fwrap.is_defined
    signature_hints = spe_fwrap.get_signature_hints()
    assert signature_hints["x"].match(int)
    assert signature_hints["return"].match(int)

    unspe_fwrap = spe_fwrap.unspecialize()
    assert unspe_fwrap.is_generic
    assert unspe_fwrap.is_defined
    signature_hints = unspe_fwrap.get_signature_hints()
    assert signature_hints["x"] is wrap_type(Any)

    respe_fwrap = unspe_fwrap.specialize((wrap_type(str),))
    assert respe_fwrap.is_generic
    assert respe_fwrap.is_defined
    signature_hints = respe_fwrap.get_signature_hints()
    assert signature_hints["x"].match(str)
    assert signature_hints["return"].match(str)


def test_wrap_specialize_generic_function_from_return() -> None:
    class GenericClass[T, V]: ...

    def generic_func[T, V](x: T, y: V) -> GenericClass[V, T]: ...

    fwrap = wrap_func(generic_func)

    with pytest.raises(UnresolvedTypeVarError):
        fwrap.get_signature_hints()
    assert not fwrap.is_defined
    assert fwrap.is_generic

    spe_fwrap = fwrap.specialize_from_return(wrap_type(GenericClass[int, str]))
    assert spe_fwrap.is_generic
    assert spe_fwrap.is_defined
    signature_hints = spe_fwrap.get_signature_hints()
    assert signature_hints["x"].match(str)
    assert signature_hints["y"].match(int)
    assert signature_hints["return"].match(GenericClass[int, str])


def test_fail_wrap_specialize_from_return_missing_param() -> None:
    class GenericClass[T]: ...

    def generic_func[T, V](x: T, y: V, z: V) -> GenericClass[T]: ...

    fwrap = wrap_func(generic_func)

    with pytest.raises(UnresolvedTypeVarError):
        fwrap.get_signature_hints()
    assert not fwrap.is_defined
    assert fwrap.is_generic

    with pytest.raises(UnresolvedFunctionTypeVarsError) as exc_info:
        fwrap.specialize_from_return(wrap_type(GenericClass[int]))

    assert exc_info.value.func_name == "test_fail_wrap_specialize_from_return_missing_param.<locals>.generic_func"
    assert exc_info.value.typevars == ["T", "V"]
    assert (
        str(exc_info.value)
        == "TypeVars T, V in function test_fail_wrap_specialize_from_return_missing_param.<locals>.generic_func "
        "could not be inferred from context"
    )


def test_wrap_specialize_non_generic_function() -> None:
    def func(x: int) -> int: ...

    assert wrap_func(func).specialize((wrap_type(str),)) is wrap_func(func)


def test_get_annotations_from_func_params() -> None:
    def func(x: Annotated[int, "test"]) -> None: ...

    wrap = wrap_func(func)

    sig = wrap.get_signature_hints()
    assert "x" in sig

    anno_x = sig["x"]
    assert anno_x.annotations == ("test",)
