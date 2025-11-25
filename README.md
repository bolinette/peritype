# Peritype

Peritype helps you navigate Python types and annotations at runtime with ease.
It provides a standard interface to inspect the mess of types, generics, `TypeVar`s, `Annotated`s, and more.

## Installation

```shell
$ pip install peritype  # or use your preferred package manager
```

## Features

### Simple type wrapping

```python
from peritype import wrap_type

class MyClass:
    attr: int

    def __init__(self, x: int, y: str) -> None:
        self.x = x
        self.y = y

    def my_method(self, z: float) -> bool:
        return z > 0.0

wrapped = wrap_type(MyClass)

# Test if the type can match another type
assert wrapped.match(MyClass)
assert not wrapped.match(int)

# Access attribute type hints
hints = wrapped.attribute_hints
assert hints['attr'].match(int)

# Access the __init__ method's signature hints
init_signature = wrapped.init.get_signature_hints()
assert init_signature['x'].match(int)
assert init_signature['y'].match(str)

# Access method signatures
method_wrap = wrapped.get_method_hints('my_method')
method_signature = method_wrap.get_signature_hints()
assert method_signature['z'].match(float)
assert method_wrap.return_hint.match(bool)
```

### Generic type wrapping

```python
from peritype import wrap_type

class GenericParent[T]:
    def get_value(self) -> T:
        ...

class GenericChild[T, U](GenericParent[U]):
    def get_other_value(self) -> T:
        ...

wrapped_child = wrap_type(GenericChild[int, str])

# Access method signatures with resolved generics
get_value_wrap = wrapped_child.get_method_hints('get_value')
get_value_signature = get_value_wrap.get_signature_hints()
assert get_value_wrap.get_return_hint().match(str)

get_other_value_wrap = wrapped_child.get_method_hints('get_other_value')
get_other_value_signature = get_other_value_wrap.get_signature_hints()
assert get_other_value_wrap.get_return_hint().match(int)
```

### Union and `Any` handling

```python
from peritype import wrap_type

int_wrap = wrap_type(int)
# A simple type can match itself and unions including itself
assert int_wrap.match(int)
assert int_wrap.match(int | str)
assert not int_wrap.match(str)

union_wrap = wrap_type(int | str)
# A union type can match any of its member types and unions including them
assert union_wrap.match(int | str)
assert union_wrap.match(int)
assert union_wrap.match(str)
assert union_wrap.match(int | float)
assert not union_wrap.match(float)

int_list_wrap = wrap_type(list[int])
# A generic type with parameters can match the same generic with compatible parameters, including Any or Ellipsis
assert int_list_wrap.match(list[int])
assert int_list_wrap.match(list[int | str])
assert int_list_wrap.match(list[Any])
```

### Type metadata, `Annotated` and more

```python
from peritype import wrap_type
from typing import Annotated, NotRequired, TypedDict

annotated_wrap = wrap_type(Annotated[int | None, "metadata"])

assert annotated_wrap.nullable  # None in the union
assert not annotated_wrap.union  # int | None is not considered a union, the None part is handled separately
assert annotated_wrap.annotations == ("metadata",)

class MyTypedDict(TypedDict, total=False):
    x: int
    y: NotRequired[str]

typed_dict_wrap = wrap_type(MyTypedDict)
assert not typed_dict_wrap.total

attrs = typed_dict_wrap.attribute_hints
assert attrs["x"].match(int)
assert attrs["y"].match(str)
assert attrs["x"].required
assert not attrs["y"].required
```

### Function wrapping

```python
from peritype import wrap_func

def my_function(a: int, b: str) -> bool:
    return str(a) == b

wrapped_func = wrap_func(my_function)

# Access function signature hints
signature_hints = wrapped_func.get_signature_hints()
assert signature_hints['a'].match(int)
assert signature_hints['b'].match(str)
assert wrapped_func.get_return_hint().match(bool)
```