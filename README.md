# Peritype

Peritype helps you navigate Python types and annotations at runtime with ease.
It provides a standard interface to inspect the mess of types, generics, `TypeVar`s, `Annotated`s, and more.

Peritype is designed to be lightweight and dependency-free.
It uses a built-in type wrapper to provide a consistent interface for inspecting types, their attributes, methods, and signature hints.
The wrappers are cached by default to improve performance and avoid redundant computations.

```python
from peritype import wrap_type

class Repository[T]:
    items: list[T]

    def get(self, index: int) -> T:
        return self.items[index]

wrapped = wrap_type(Repository[int])

assert wrapped.attribute_hints["items"].matches(list[int])
assert wrapped.get_method("get").get_return_hint().matches(int)
assert wrapped.match(Repository[int | str]).is_exact
assert wrapped.match(Repository[str]).is_none
```

## Installation

```shell
$ pip install peritype  # or use your preferred package manager
```

## Requirements

Peritype requires Python 3.13 (or newer) and no other dependencies.

## Concepts

`wrap_type` returns a `TWrap`, which contains a `TypeNode` for each member of the type (a single one for `int`, two for `int | str`).
Every node gives access to the underlying class with `inner_type` and to the wrapped generic parameters with `generic_params`.

Optional types are not considered unions: `int | None` has `nullable` set and `union` unset, and the `None` part is kept aside so that `inner_type`, `attribute_hints` and the other single-type accessors still work.

`Annotated` arguments, `NotRequired`/`Required` markers and `TypedDict` totality are not part of the nodes.
They are stored on the wrapper and available through `annotations`, `required` and `total`.

Wrapping the same type twice returns the same wrapper, and different spellings of the same type (`Optional[int]` and `int | None`) compare equal.
The cache can be disabled with `peritype.utils.use_cache(False)`.

## Wrapping a type

The `TWrap` type wrapper can be used to inspect a type's attributes, methods, and signature hints.
Wrappers can also be used to check if a type matches another type, including unions and generics.

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
assert wrapped.matches(MyClass)
assert not wrapped.matches(int)

# Access attribute type hints
hints = wrapped.attribute_hints
assert hints['attr'].matches(int)

# Access the __init__ method's signature hints
init_signature = wrapped.init.get_signature_hints()
assert init_signature['x'].matches(int)
assert init_signature['y'].matches(str)

# Access method signatures
method_wrap = wrapped.get_method('my_method')
method_signature = method_wrap.get_signature_hints()
assert method_signature['z'].matches(float)
assert method_wrap.get_return_hint().matches(bool)
```

`wrap_type` works with any type annotation: parameterized generics, unions, `Annotated`, `TypedDict` fields and `type` aliases.

```python
from typing import Any
from peritype import wrap_type

type Names = list[str]

assert wrap_type(list) == wrap_type(list[Any])       # missing type parameters default to Any
assert wrap_type(Names) == wrap_type(list[str])      # type aliases are resolved to their value
assert str(wrap_type(dict[str, list[int]])) == "dict[str, list[int]]"
assert wrap_type(dict[str, list[int]]).generic_params[1].matches(list[int])
```

Wrapping a `TypeVar` on its own, or a forward reference that cannot be resolved, raises `UnresolvedTypeVarError` or `UnresolvedForwardRefError`.
`TypeVar`s are resolved when wrapping a parameterized class, see [Generic type wrapping](#generic-type-wrapping).

### Type metadata, `Annotated` and more

Annotated types expose their metadata through the wrapper, and `TypedDict`s can be inspected for their attributes and whether they are required or optional.

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
assert attrs["x"].matches(int)
assert attrs["y"].matches(str)
assert attrs["x"].required
assert not attrs["y"].required
```

`inner_type`, `generic_params`, `attribute_hints`, `init`, `get_method` and `instantiate` only make sense on a single type, and raise a `TypeError` on unions like `int | str`.

## Matching

`matches` returns a boolean, `match` returns a `MatchResult` that tells how the types matched: `exact`, `lineage` (through inheritance), `catchall` (through `Any` or `...`) or `none`.
Results can be compared to find the strongest match, and a result is truthy unless it is `none`.

### Union and `Any` handling

```python
from typing import Any
from peritype import wrap_type

int_wrap = wrap_type(int)
# A simple type can match itself and unions including itself
assert int_wrap.matches(int)
assert int_wrap.matches(int | str)
assert not int_wrap.matches(str)

union_wrap = wrap_type(int | str)
# A union type can match any of its member types and unions including them
assert union_wrap.matches(int | str)
assert union_wrap.matches(int)
assert union_wrap.matches(str)
assert union_wrap.matches(int | float)
assert not union_wrap.matches(float)

int_list_wrap = wrap_type(list[int])
# A generic type with parameters can match the same generic with compatible parameters, including Any or Ellipsis
assert int_list_wrap.matches(list[int])
assert int_list_wrap.matches(list[int | str])
assert int_list_wrap.matches(list[Any])

# Any matches anything, but the result is only a catchall, and strict mode rejects it
assert int_wrap.match(int).is_exact
assert int_wrap.match(Any).is_catchall
assert int_list_wrap.match(list[Any]).is_catchall  # the match is only as strong as the weakest parameter
assert not int_wrap.matches(Any, strict=True)
```

### Inheritance

By default, a type only matches itself.
With `lineage="super"`, the wrapped type also matches its parent types, with `"sub"` it matches its subtypes, and `"both"` combines the two.

```python
from peritype import wrap_type

class Animal[T]: ...
class Dog(Animal[str]): ...

assert not wrap_type(Dog).matches(Animal[str])
assert wrap_type(Dog).match(Animal[str], lineage="super").is_lineage
assert wrap_type(Animal[str]).match(Dog, lineage="sub").is_lineage
assert wrap_type(Dog).match(Animal[int], lineage="super").is_none
```

### Checking values

`is_type_of` checks a value against the wrapper, like `isinstance` would, including subclasses.
Instances created from a parameterized class (`Animal[str]()`) keep their type parameters and are checked against them, but the content of plain containers is not inspected.

```python
from peritype import wrap_type

class Animal[T]: ...
class Dog(Animal[str]): ...

assert wrap_type(Animal[str]).is_type_of(Dog())
assert wrap_type(Animal[str]).is_type_of(Animal[str]())
assert not wrap_type(Animal[str]).is_type_of(Animal[int]())
assert wrap_type(list[int]).is_type_of(["a", "b"])  # list content is not checked
```

## Generic type wrapping

Python generics can be tricky to work with at runtime, but `peritype` provides a way to wrap generic types and resolve their type parameters.
`TypeVar`s are propagated through the type hierarchy, allowing you to inspect methods and attributes with their resolved types.

```python
from peritype import wrap_type

class GenericParent[T]:
    value: T

    def get_value(self) -> T:
        ...

class GenericChild[T, U](GenericParent[U]):
    def get_other_value(self) -> T:
        ...

wrapped_child = wrap_type(GenericChild[int, str])

# Access attributes with resolved generics
assert wrapped_child.attribute_hints['value'].matches(str)

# Access method signatures with resolved generics
get_value_wrap = wrapped_child.get_method('get_value')
assert get_value_wrap.get_return_hint().matches(str)

get_other_value_wrap = wrapped_child.get_method('get_other_value')
assert get_other_value_wrap.get_return_hint().matches(int)
```

A generic class wrapped without parameters gets `Any` for each of them.
`specialize_with` replaces them with the parameters of another wrapper, which can be a parent or a child type.

```python
from peritype import wrap_type

class Box[T]: ...
class SubBox[T](Box[T]): ...

assert wrap_type(SubBox).specialize_with(wrap_type(Box[int])) == wrap_type(SubBox[int])
assert wrap_type(Box).specialize_with(wrap_type(SubBox[int])) == wrap_type(Box[int])
```

## Function wrapping

```python
from peritype import wrap_func

def my_function(a: int, b: str) -> bool:
    return str(a) == b

wrapped_func = wrap_func(my_function)

# Access function signature hints
signature_hints = wrapped_func.get_signature_hints()
assert signature_hints['a'].matches(int)
assert signature_hints['b'].matches(str)
assert wrapped_func.get_signature_hint(0).matches(int)
assert wrapped_func.get_return_hint().matches(bool)
assert wrapped_func(1, "1")
```

The hints of a generic function cannot be read until its `TypeVar`s are given a value, with `specialize`, `specialize_from_return` or `unspecialize`.

```python
from typing import Any
from peritype import wrap_func, wrap_type

def first[T](items: list[T]) -> T:
    return items[0]

wrapped_func = wrap_func(first)
assert wrapped_func.is_generic and not wrapped_func.is_defined

specialized = wrapped_func.specialize([wrap_type(int)])
assert specialized.get_signature_hints()['items'].matches(list[int])

from_return = wrapped_func.specialize_from_return(wrap_type(str))
assert from_return.get_signature_hints()['items'].matches(list[str])

assert wrapped_func.unspecialize().get_return_hint().matches(Any)
```

## Collections

`TypeBag` is a set of wrappers that can be searched by matching instead of equality.
`match_all` returns the entries that match along with their `MatchResult`, `best_matching` returns the strongest of them, and both take the same `strict` and `lineage` arguments as `match`.

```python
from typing import Any
from peritype import wrap_type
from peritype.collections import TypeBag, TypeMap

bag = TypeBag[Any]()
bag.add(wrap_type(list[Any]))
bag.add(wrap_type(list[int | str]))

assert bag.best_matching(wrap_type(list[int])) == wrap_type(list[int | str])
assert bag.match_all(wrap_type(list[int]))[wrap_type(list[Any])].is_catchall
assert not bag.contains_matching(wrap_type(dict[str, int]))

handlers = TypeMap[Any, str]()
handlers[wrap_type(int | None)] = "optional int"
assert handlers[wrap_type(None | int)] == "optional int"  # equal wrappers are the same key
```

`TypeSuperTree` registers a wrapper under each of its parent types, to retrieve all the registered subtypes of a given type in one lookup.

```python
from peritype import wrap_type
from peritype.collections import TypeSuperTree

class Animal[T]: ...
class Dog(Animal[str]): ...

tree = TypeSuperTree()
tree.add(wrap_type(Dog))
assert tree[wrap_type(Animal[str])] == {wrap_type(Dog)}
assert wrap_type(Animal[int]) not in tree
```

## Reference

### Supported constructs

| Construct                                                               | Behaviour                                                                          |
| ----------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| Classes, builtins, `None`                                               | Wrapped as a single node                                                           |
| `list[int]`, `dict[str, T]`, user generics (PEP 695 and `Generic[T]`)   | Parameters are wrapped recursively, missing ones default to `Any`                  |
| `X \| Y`, `Union`, `Optional`                                           | One node per member, `None` sets `nullable`                                        |
| `Annotated`, `NotRequired`, `Required`, `ReadOnly`, `ClassVar`, `Final` | Removed from the type, kept as metadata                                            |
| `type` aliases, generic aliases                                         | Expanded to their value                                                            |
| `Literal[...]`                                                          | Values are compared by type and value, a literal does not match its base type      |
| `Callable[[A], R]`, `ParamSpec`, `...`                                  | Parameter lists are matched position by position, `...` matches any of them        |
| Bare `TypeVar`, forward references                                      | Raise an error unless resolved through a parameterized class or an explicit lookup |

Not supported yet: tuple variadics (`tuple[int, ...]` is not matched against `tuple[int, int]`), structural matching of `Protocol`s, `TypeVar` bounds and variance, `NewType`, `Self`, and `functools.partial` or callable objects in `wrap_func`.

### Errors

All errors derive from `peritype.errors.PeritypeError`.

| Error                             | Raised when                                               |
| --------------------------------- | --------------------------------------------------------- |
| `UnresolvedTypeVarError`          | A `TypeVar` has no value in the current context           |
| `UnresolvedForwardRefError`       | A string annotation cannot be resolved                    |
| `IncompatibleTypesError`          | `specialize_with` is given a wrap of an unrelated family  |
| `UnresolvedFunctionTypeVarsError` | `specialize_from_return` cannot infer every type variable |
