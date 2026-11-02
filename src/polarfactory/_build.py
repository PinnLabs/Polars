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


def build(cls: type[T], /, *, seed: int | None = None, **overrides: object) -> T:
    if not (isinstance(cls, type) and dataclasses.is_dataclass(cls)):
        raise TypeError(f"build() expects a dataclass, got {cls!r}")

    fields = dataclasses.fields(cls)
    init_by_name = {field.name: field.init for field in fields}
    for name in overrides:
        if name not in init_by_name:
            valid = ", ".join(field.name for field in fields if field.init)
            raise TypeError(
                f"build() got unknown field '{name}' for {cls.__name__}; valid fields: {valid}"
            )
        if not init_by_name[name]:
            raise TypeError(f"build() cannot set field '{cls.__name__}.{name}': it has init=False")

    base_seed = random.Random().getrandbits(64) if seed is None else seed
    hints = get_type_hints(cls)
    values: dict[str, Any] = dict(overrides)
    for field in fields:
        if not field.init or field.name in overrides:
            continue
        tp = hints[field.name]
        generator = _GENERATORS.get(tp)
        if generator is None:
            raise TypeError(
                f"cannot generate field '{cls.__name__}.{field.name}' of type {_type_name(tp)}"
            )
        values[field.name] = generator(random.Random(f"{base_seed}:{field.name}"))
    return cls(**values)
