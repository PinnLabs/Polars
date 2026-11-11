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

from polarfactory.errors import GenerationError, PolarFactoryError

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


_DEFAULT_GENERATORS: dict[Any, Callable[[random.Random], Any]] = {
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
_GENERATORS = dict(_DEFAULT_GENERATORS)


def register(tp: type[T], fn: Callable[[random.Random], T]) -> None:
    if not callable(fn):
        raise PolarFactoryError(f"register() expects a callable for {tp!r}, got {fn!r}")
    _GENERATORS[tp] = fn


def reset_registry() -> None:
    _GENERATORS.clear()
    _GENERATORS.update(_DEFAULT_GENERATORS)


def _type_name(tp: Any) -> str:
    return str(tp) if get_origin(tp) else getattr(tp, "__name__", str(tp))


class _DepthExceededError(GenerationError):
    pass


def _override_hint(path: str) -> str:
    root, field = path.split(".")[:2]
    return f"build({root}, {field}=...)"


def _type_hints(obj: Any, cls: type[Any], namespace: dict[str, Any] | None = None) -> Any:
    try:
        return get_type_hints(obj, namespace)
    except NameError as exc:
        raise GenerationError(
            f"cannot resolve type hints of {cls.__name__}: {exc}. "
            f"Define or import it in module '{cls.__module__}'"
        ) from exc


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


def _field_specs(cls: type[Any]) -> list[_FieldSpec]:
    if _is_dataclass_type(cls):
        hints = _type_hints(cls, cls)
        specs = [
            _FieldSpec(field.name, hints[field.name], field.init)
            for field in dataclasses.fields(cls)
        ]
        # InitVar pseudo-fields are __init__ arguments but not part of dataclasses.fields().
        return specs + [
            _FieldSpec(name, hint.type)
            for name, hint in hints.items()
            if isinstance(hint, dataclasses.InitVar)
        ]
    hints = _type_hints(cls.__init__, cls)
    params = list(inspect.signature(cls.__init__).parameters.values())[1:]  # drop self
    return [
        # A missing hint is stored as Parameter.empty so an override can still supply the value.
        _FieldSpec(param.name, hints.get(param.name, param.empty))
        for param in params
        if param.kind not in (param.VAR_POSITIONAL, param.VAR_KEYWORD)
    ]


def _resolve_forward_ref(tp: str, owner: type) -> Any:
    # shortcut: Python 3.10 leaves list["X"] unresolved, and this only looks in owner's module, so
    # a field inherited from another module raises NameError. Drop this when 3.10 support ends.
    holder = types.SimpleNamespace(__annotations__={"value": tp})
    return _type_hints(holder, owner, vars(sys.modules[owner.__module__]))["value"]


_COLLECTION_HINTS: dict[Any, str] = {
    list: "list[X]",
    set: "set[X]",
    dict: "dict[K, V]",
    tuple: "tuple[X, Y] or tuple[X, ...]",
}


def _generate_items(
    tp: Any, seed: str, path: str, ancestors: tuple[type, ...], suffix: str = ""
) -> list[Any]:
    # The length depends only on seed, so dict keys and values get the same length.
    length = random.Random(seed).randint(1, 3)
    try:
        return [_generate(tp, f"{seed}:{i}{suffix}", path, ancestors) for i in range(length)]
    except _DepthExceededError:
        return []


def _generate_collection(
    kind: type, tp: Any, seed: str, path: str, ancestors: tuple[type, ...]
) -> Any:
    args = get_args(tp)
    if not args:
        raise GenerationError(
            f"cannot generate field '{path}' of type {kind.__name__}. "
            f"Use {_COLLECTION_HINTS[kind]}, or pass it as an override: {_override_hint(path)}"
        )
    if kind is tuple and args[-1] is not Ellipsis:
        return tuple(_generate(arg, f"{seed}:{i}", path, ancestors) for i, arg in enumerate(args))
    items = _generate_items(args[0], seed, path, ancestors)
    if kind is list:
        return items
    if kind is tuple:
        return tuple(items)
    values = _generate_items(args[1], seed, path, ancestors, ":value") if kind is dict else []
    try:
        return dict(zip(items, values, strict=False)) if kind is dict else set(items)
    except TypeError as exc:
        what = "keys" if kind is dict else "items"
        raise GenerationError(
            f"cannot generate field '{path}' of type {_type_name(tp)}: {what} are not hashable. "
            f"Use a hashable type, or pass it as an override: {_override_hint(path)}"
        ) from exc


def _generate_union(members: list[Any], seed: str, path: str, ancestors: tuple[type, ...]) -> Any:
    # Generate every member so an unsupported one fails no matter which member the seed picks.
    values = []
    depth_errors = []
    for i, member in enumerate(members):
        try:
            values.append(_generate(member, f"{seed}:{i}", path, ancestors))
        except _DepthExceededError as exc:
            depth_errors.append(exc)
    if not values:
        raise depth_errors[0]
    return random.Random(seed).choice(values)


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
            f"required self-reference exceeds max depth {_MAX_DEPTH}. "
            f"Make it Optional or a list, or pass it as an override: {_override_hint(path)}"
        )
    values: dict[str, Any] = dict(overrides)
    for field in _field_specs(cls):
        if field.init and field.name not in overrides:
            field_path = f"{path}.{field.name}"
            if field.type is inspect.Parameter.empty:
                raise GenerationError(
                    f"cannot generate field '{field_path}': parameter '{field.name}' of "
                    f"{cls.__name__}.__init__ has no type hint. "
                    f"Add one, or pass it as an override: {_override_hint(field_path)}"
                )
            values[field.name] = _generate(
                field.type, f"{seed}:{field.name}", field_path, ancestors
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
            raise GenerationError(
                f"cannot generate field '{path}' of type {tp.__name__}: enum has no members. "
                f"Add a member, or pass it as an override: {_override_hint(path)}"
            )
        return random.Random(seed).choice(members)
    if _is_buildable(tp):
        return _generate_object(tp, seed, path, ancestors, {})
    kind = origin or tp
    if kind in _COLLECTION_HINTS:
        return _generate_collection(kind, tp, seed, path, ancestors)
    if origin in (Union, types.UnionType):
        args = get_args(tp)
        inner = [arg for arg in args if arg is not type(None)]
        if len(inner) < len(args):
            core = inner[0] if len(inner) == 1 else Union[tuple(inner)]  # noqa: UP007 - built at runtime
            return _generate_optional(core, seed, path, ancestors)
        return _generate_union(inner, seed, path, ancestors)
    raise GenerationError(
        f"cannot generate field '{path}' of type {_type_name(tp)}. "
        f"Pass it as an override: {_override_hint(path)}"
    )


def _check_build_args(func: str, cls: type[Any], overrides: dict[str, object]) -> None:
    if not _is_buildable(cls):
        raise PolarFactoryError(
            f"{func}() expects a dataclass or a class with __init__, got {cls!r}"
        )

    fields = _field_specs(cls)
    init_by_name = {field.name: field.init for field in fields}
    for name in overrides:
        if name not in init_by_name:
            valid = ", ".join(field.name for field in fields if field.init)
            raise PolarFactoryError(
                f"{func}() got unknown field '{name}' for {cls.__name__}; valid fields: {valid}"
            )
        if not init_by_name[name]:
            raise PolarFactoryError(
                f"{func}() cannot set field '{cls.__name__}.{name}': it has init=False. "
                "Set it on the built object instead"
            )


def _base_seed(seed: int | None) -> int:
    return random.Random().getrandbits(64) if seed is None else seed


def build(cls: type[T], /, *, seed: int | None = None, **overrides: object) -> T:
    _check_build_args("build", cls, overrides)
    root_seed = str(_base_seed(seed))
    return cast(T, _generate_object(cls, root_seed, cls.__name__, (), overrides))


def build_many(cls: type[T], n: int, /, *, seed: int | None = None, **overrides: object) -> list[T]:
    _check_build_args("build_many", cls, overrides)
    if n < 0:
        raise PolarFactoryError(f"build_many() expects n >= 0, got {n}")
    base_seed = _base_seed(seed)
    return [
        cast(T, _generate_object(cls, f"{base_seed}:{i}", cls.__name__, (), overrides))
        for i in range(n)
    ]
