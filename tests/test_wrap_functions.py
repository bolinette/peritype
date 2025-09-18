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
    assert fwrap.annotation(0).match(int)
    assert fwrap.annotation(1).match(str)
    annotations = fwrap.annotations()
    assert annotations["x"].match(int)
    assert annotations["y"].match(str)
    assert annotations["return"].match(bool)
    assert fwrap.return_type.match(bool)


def test_wrap_init_with_typevar() -> None:
    class TestType[T]:
        def __init__(self, value: T) -> None: ...

    twrap = wrap_type(TestType[int])
    fwrap = wrap_func(getattr(TestType, "__init__"))  # noqa: B009

    annotations = fwrap.annotations(belongs_to=twrap)
    assert annotations["value"].match(int)
    assert annotations["return"].match(None)


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

    annotations = fwrap_child.annotations(belongs_to=twrap)
    assert annotations["value"].match(bool)
    assert annotations["return"].match(None)
    annotations = fwrap_super.annotations(belongs_to=twrap)
    assert annotations["value"].match(int)
    assert annotations["return"].match(None)
    annotations = fwrap_super_super.annotations(belongs_to=twrap)
    assert annotations["value"].match(float)
    assert annotations["return"].match(None)


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

    annotations = fwrap_child.annotations(belongs_to=twrap)
    assert annotations["value"].match(P1)
    assert annotations["return"].match(None)
    annotations = fwrap_super.annotations(belongs_to=twrap)
    assert annotations["value"].match(P2)
    assert annotations["return"].match(None)
    annotations = fwrap_super_super.annotations(belongs_to=twrap)
    assert annotations["value"].match(P3)
    assert annotations["return"].match(None)


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

    annotations = fwrap1.annotations(belongs_to=twrap)
    assert annotations["value"].match(P1)
    assert annotations["return"].match(None)
    annotations = fwrap2.annotations(belongs_to=twrap)
    assert annotations["value"].match(P2)
    assert annotations["return"].match(None)
