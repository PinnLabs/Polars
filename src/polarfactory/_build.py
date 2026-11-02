import dataclasses
import random
import string
import sys
import types
from collections.abc import Callable
from typing import Any, TypeVar, Union, cast, get_args, get_origin, get_type_hints

T = TypeVar("T")

_MAX_DEPTH = 3
_NONE_PROBABILITY = 0.25


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


class _DepthExceededError(TypeError):
    pass


def _is_dataclass_type(tp: Any) -> bool:
    return isinstance(tp, type) and dataclasses.is_dataclass(tp)


def _resolve_forward_ref(tp: str, owner: type) -> Any:
    # shortcut: Python 3.10 leaves list["X"] unresolved, and this only looks in owner's module, so
    # a field inherited from another module raises NameError. Drop this when 3.10 support ends.
    holder = types.SimpleNamespace(__annotations__={"value": tp})
    return get_type_hints(holder, vars(sys.modules[owner.__module__]))["value"]


def _generate_list(tp: Any, seed: str, path: str, ancestors: tuple[type, ...]) -> list[Any]:
    args = get_args(tp)
    if not args:
        raise TypeError(f"cannot generate field '{path}' of type list: use list[X]")
    length = random.Random(seed).randint(1, 3)
    try:
        return [_generate(args[0], f"{seed}:{i}", path, ancestors) for i in range(length)]
    except _DepthExceededError:
        return []


def _generate_optional(tp: Any, seed: str, path: str, ancestors: tuple[type, ...]) -> Any:
    try:
        value = _generate(tp, f"{seed}:value", path, ancestors)
    except _DepthExceededError:
        return None
    return None if random.Random(seed).random() < _NONE_PROBABILITY else value


def _generate_dataclass(
    cls: type[Any],
    seed: str,
    path: str,
    ancestors: tuple[type, ...],
    overrides: dict[str, object],
) -> Any:
    ancestors = (*ancestors, cls)
    if len(ancestors) - len(set(ancestors)) > _MAX_DEPTH:
        raise _DepthExceededError(
            f"cannot generate field '{path}' of type {cls.__name__}: "
            f"required self-reference exceeds max depth {_MAX_DEPTH}"
        )
    hints = get_type_hints(cls)
    values: dict[str, Any] = dict(overrides)
    for field in dataclasses.fields(cls):
        if field.init and field.name not in overrides:
            values[field.name] = _generate(
                hints[field.name], f"{seed}:{field.name}", f"{path}.{field.name}", ancestors
            )
    return cls(**values)


def _generate(tp: Any, seed: str, path: str, ancestors: tuple[type, ...]) -> Any:
    if isinstance(tp, str):
        tp = _resolve_forward_ref(tp, ancestors[-1])
    generator = _GENERATORS.get(tp)
    if generator is not None:
        return generator(random.Random(seed))
    if _is_dataclass_type(tp):
        return _generate_dataclass(tp, seed, path, ancestors, {})
    origin = get_origin(tp)
    if tp is list or origin is list:
        return _generate_list(tp, seed, path, ancestors)
    if origin in (Union, types.UnionType):
        inner = [arg for arg in get_args(tp) if arg is not type(None)]
        if len(inner) == 1:
            return _generate_optional(inner[0], seed, path, ancestors)
    raise TypeError(f"cannot generate field '{path}' of type {_type_name(tp)}")


def build(cls: type[T], /, *, seed: int | None = None, **overrides: object) -> T:
    if not _is_dataclass_type(cls):
        raise TypeError(f"build() expects a dataclass, got {cls!r}")

    fields = dataclasses.fields(cast(Any, cls))
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
    return cast(T, _generate_dataclass(cls, str(base_seed), cls.__name__, (), overrides))
