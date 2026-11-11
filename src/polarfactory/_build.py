import dataclasses
import inspect
import random
import string
import sys
import types
from collections.abc import Callable
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Literal, TypeVar, Union, cast, get_args, get_origin, get_type_hints
from uuid import UUID

T = TypeVar("T")

_MAX_DEPTH = 3
_NONE_PROBABILITY = 0.25
_DATE_ANCHOR = datetime(2025, 1, 1, tzinfo=timezone.utc)
_DATE_WINDOW = timedelta(days=5 * 365)


def _generate_int(rng: random.Random) -> int:
    return rng.randint(0, 10_000)


def _generate_str(rng: random.Random) -> str:
    return "".join(rng.choices(string.ascii_lowercase, k=8))


def _generate_bool(rng: random.Random) -> bool:
    return rng.random() < 0.5


def _generate_float(rng: random.Random) -> float:
    return round(rng.uniform(0, 10_000), 2)


def _generate_bytes(rng: random.Random) -> bytes:
    return rng.randbytes(8)


def _generate_datetime(rng: random.Random) -> datetime:
    return _DATE_ANCHOR - timedelta(seconds=rng.randrange(int(_DATE_WINDOW.total_seconds())))


def _generate_date(rng: random.Random) -> date:
    return _DATE_ANCHOR.date() - timedelta(days=rng.randrange(_DATE_WINDOW.days))


def _generate_time(rng: random.Random) -> time:
    return time(rng.randrange(24), rng.randrange(60), rng.randrange(60))


def _generate_timedelta(rng: random.Random) -> timedelta:
    return timedelta(seconds=rng.randint(0, 30 * 24 * 60 * 60))


def _generate_uuid(rng: random.Random) -> UUID:
    return UUID(int=rng.getrandbits(128), version=4)


def _generate_decimal(rng: random.Random) -> Decimal:
    return Decimal(f"{rng.randint(0, 1_000_000) / 100:.2f}")


_GENERATORS: dict[Any, Callable[[random.Random], Any]] = {
    int: _generate_int,
    str: _generate_str,
    bool: _generate_bool,
    float: _generate_float,
    bytes: _generate_bytes,
    datetime: _generate_datetime,
    date: _generate_date,
    time: _generate_time,
    timedelta: _generate_timedelta,
    UUID: _generate_uuid,
    Decimal: _generate_decimal,
}


def _type_name(tp: Any) -> str:
    return str(tp) if get_origin(tp) else getattr(tp, "__name__", str(tp))


class _DepthExceededError(TypeError):
    pass


@dataclasses.dataclass(frozen=True)
class _FieldSpec:
    name: str
    type: Any
    init: bool = True


def _is_dataclass_type(tp: Any) -> bool:
    return isinstance(tp, type) and dataclasses.is_dataclass(tp)


def _is_buildable(tp: Any) -> bool:
    # A Python-defined __init__ marks a plain class; builtins like complex use slot wrappers.
    return _is_dataclass_type(tp) or (
        isinstance(tp, type) and inspect.isfunction(getattr(tp, "__init__", None))
    )


def _field_specs(cls: type[Any], path: str) -> list[_FieldSpec]:
    if _is_dataclass_type(cls):
        hints = get_type_hints(cls)
        return [_FieldSpec(f.name, hints[f.name], f.init) for f in dataclasses.fields(cls)]
    hints = get_type_hints(cls.__init__)
    params = list(inspect.signature(cls.__init__).parameters.values())[1:]  # drop self
    specs = []
    for param in params:
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            continue
        if param.name not in hints:
            raise TypeError(
                f"cannot generate field '{path}.{param.name}': "
                f"parameter '{param.name}' of {cls.__name__}.__init__ has no type hint"
            )
        specs.append(_FieldSpec(param.name, hints[param.name]))
    return specs


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


def _generate_object(
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
    values: dict[str, Any] = dict(overrides)
    for field in _field_specs(cls, path):
        if field.init and field.name not in overrides:
            values[field.name] = _generate(
                field.type, f"{seed}:{field.name}", f"{path}.{field.name}", ancestors
            )
    return cls(**values)


def _generate(tp: Any, seed: str, path: str, ancestors: tuple[type, ...]) -> Any:
    if isinstance(tp, str):
        tp = _resolve_forward_ref(tp, ancestors[-1])
    generator = _GENERATORS.get(tp)
    if generator is not None:
        return generator(random.Random(seed))
    origin = get_origin(tp)
    if origin is Literal:
        return random.Random(seed).choice(get_args(tp))
    if origin is None and isinstance(tp, type) and issubclass(tp, Enum):
        members = list(tp)
        if not members:
            raise TypeError(
                f"cannot generate field '{path}' of type {tp.__name__}: enum has no members"
            )
        return random.Random(seed).choice(members)
    if _is_buildable(tp):
        return _generate_object(tp, seed, path, ancestors, {})
    if tp is list or origin is list:
        return _generate_list(tp, seed, path, ancestors)
    if origin in (Union, types.UnionType):
        inner = [arg for arg in get_args(tp) if arg is not type(None)]
        if len(inner) == 1:
            return _generate_optional(inner[0], seed, path, ancestors)
    raise TypeError(f"cannot generate field '{path}' of type {_type_name(tp)}")


def build(cls: type[T], /, *, seed: int | None = None, **overrides: object) -> T:
    if not _is_buildable(cls):
        raise TypeError(f"build() expects a dataclass or a class with __init__, got {cls!r}")

    fields = _field_specs(cls, cls.__name__)
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
    return cast(T, _generate_object(cls, str(base_seed), cls.__name__, (), overrides))
