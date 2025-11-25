from peritype import FWrap, wrap_func, wrap_type


def test_wrap_basic_func() -> None:
    def func(x: int, y: str) -> bool: ...

    fwrap = wrap_func(func)
    assert isinstance(fwrap, FWrap)
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
