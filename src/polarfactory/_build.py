import dataclasses
import random
import string
from collections.abc import Callable
from typing import Any, TypeVar, get_origin, get_type_hints

T = TypeVar("T")


def _generate_int(rng: random.Random) -> int:
    return rng.randint(0, 10_000)


def _generate_str(rng: random.Random) -> str:
    return "".join(rng.choices(string.ascii_lowercase, k=8))


def _generate_bool(rng: random.Random) -> bool:
    return rng.random() < 0.5


_GENERATORS: dict[Any, Callable[[random.Random], Any]] = {
    int: _generate_int,
    str: _generate_str,
    bool: _generate_bool,
}


def _type_name(tp: Any) -> str:
    return str(tp) if get_origin(tp) else getattr(tp, "__name__", str(tp))


def build(cls: type[T]) -> T:
    """Create an instance of a dataclass with its fields filled with random values."""
    if not (isinstance(cls, type) and dataclasses.is_dataclass(cls)):
        raise TypeError(f"build() expects a dataclass, got {cls!r}")

    rng = random.Random()
    hints = get_type_hints(cls)
    values: dict[str, Any] = {}
    for field in dataclasses.fields(cls):
        if not field.init:
            continue
        tp = hints[field.name]
        generator = _GENERATORS.get(tp)
        if generator is None:
            raise TypeError(
                f"cannot generate field '{cls.__name__}.{field.name}' of type {_type_name(tp)}"
            )
        values[field.name] = generator(rng)
    return cls(**values)
