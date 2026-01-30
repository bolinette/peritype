from peritype.utils import WithOriginClass, WithParameters, WithTypeParams, is_generic
from peritype.utils._typing import WithOriginBases


def test_class_is_generic() -> None:
    class GenericClass[T]: ...

    class GenericChild(GenericClass[int]): ...

    assert is_generic(GenericClass)
    assert is_generic(GenericClass[int])
    assert is_generic(type(GenericClass[str]()))

    assert WithParameters.match(GenericClass)
    assert WithTypeParams.match(GenericClass)  # pyright: ignore[reportArgumentType]

    assert isinstance(GenericClass, type) and not WithOriginClass.match(GenericClass())
    assert WithOriginClass.match(GenericClass[int]())  # pyright: ignore[reportIndexIssue]

    assert WithOriginBases.match(GenericChild)
    assert WithOriginBases.get_origin_bases(GenericChild) == (GenericClass[int],)  # pyright: ignore[reportIndexIssue]
