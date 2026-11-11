import os
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, make_dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from enum import Enum, IntEnum
from pathlib import Path
from typing import Any, Literal
from uuid import UUID

import pytest

from polarfactory import build
from polarfactory.errors import GenerationError

SEEDS = range(50)
OPTIONS = Literal["a", "b", 1]
ANCHOR = datetime(2025, 1, 1, tzinfo=timezone.utc)
FIVE_YEARS_BEFORE_ANCHOR = datetime(2020, 1, 1, tzinfo=timezone.utc)


class Color(Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"


class Priority(IntEnum):
    LOW = 1
    HIGH = 2


class Empty(Enum):
    pass


@dataclass
class AllTypes:
    amount: float
    payload: bytes
    created: datetime
    day: date
    at: time
    wait: timedelta
    key: UUID
    price: Decimal
    color: Color
    option: OPTIONS
    maybe: datetime | None
    items: list[UUID]


@dataclass
class EmptyHolder:
    kind: Empty


@dataclass
class EmptyParent:
    inner: EmptyHolder


def is_float(value: Any) -> bool:
    return type(value) is float and 0 <= value <= 10_000 and round(value, 2) == value


def is_bytes(value: Any) -> bool:
    return type(value) is bytes and len(value) == 8


def is_datetime(value: Any) -> bool:
    return (
        type(value) is datetime
        and value.utcoffset() == timedelta(0)
        and FIVE_YEARS_BEFORE_ANCHOR <= value <= ANCHOR
    )


def is_date(value: Any) -> bool:
    return type(value) is date and FIVE_YEARS_BEFORE_ANCHOR.date() <= value <= ANCHOR.date()


def is_time(value: Any) -> bool:
    return type(value) is time


def is_timedelta(value: Any) -> bool:
    return type(value) is timedelta and timedelta(0) <= value <= timedelta(days=30)


def is_uuid(value: Any) -> bool:
    return type(value) is UUID and value.version == 4


def is_decimal(value: Any) -> bool:
    return type(value) is Decimal and 0 <= value <= 10_000 and value.as_tuple().exponent == -2


CASES: list[tuple[Any, Callable[[Any], bool]]] = [
    (float, is_float),
    (bytes, is_bytes),
    (datetime, is_datetime),
    (date, is_date),
    (time, is_time),
    (timedelta, is_timedelta),
    (UUID, is_uuid),
    (Decimal, is_decimal),
    (Color, lambda value: type(value) is Color),
    (Priority, lambda value: type(value) is Priority),
    (OPTIONS, lambda value: value in ("a", "b", 1)),
]
IDS = [str(getattr(tp, "__name__", "Literal")) for tp, _ in CASES]


def model_with(tp: Any) -> Any:
    return make_dataclass("Model", [("value", tp)])


@pytest.mark.parametrize(("tp", "is_valid"), CASES, ids=IDS)
def test_value_has_exact_type_and_range(tp: Any, is_valid: Callable[[Any], bool]) -> None:
    model = model_with(tp)
    for seed in SEEDS:
        assert is_valid(build(model, seed=seed).value)


@pytest.mark.parametrize(("tp", "is_valid"), CASES, ids=IDS)
def test_value_inside_list(tp: Any, is_valid: Callable[[Any], bool]) -> None:
    model = model_with(list[tp])
    for seed in SEEDS:
        items = build(model, seed=seed).value
        assert items and all(is_valid(item) for item in items)


@pytest.mark.parametrize(("tp", "is_valid"), CASES, ids=IDS)
def test_value_inside_optional(tp: Any, is_valid: Callable[[Any], bool]) -> None:
    model = model_with(tp | None)
    values = [build(model, seed=seed).value for seed in SEEDS]
    assert None in values
    assert all(is_valid(value) for value in values if value is not None)


@pytest.mark.parametrize(
    ("tp", "expected"),
    [(Color, set(Color)), (OPTIONS, {"a", "b", 1})],
    ids=["Enum", "Literal"],
)
def test_seeds_cover_every_enum_member_and_literal_option(tp: Any, expected: set[Any]) -> None:
    model = model_with(tp)
    assert {build(model, seed=seed).value for seed in SEEDS} == expected


def test_same_seed_gives_equal_object() -> None:
    assert build(AllTypes, seed=7) == build(AllTypes, seed=7)


def test_same_seed_gives_same_result_in_separate_processes() -> None:
    script = (
        "from polarfactory import build\n"
        "from test_common_types import AllTypes\n"
        "print(repr(build(AllTypes, seed=42)))"
    )
    outputs = {
        subprocess.run(
            [sys.executable, "-c", script],
            cwd=Path(__file__).parent,
            env={**os.environ, "PYTHONHASHSEED": hash_seed},
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        for hash_seed in ("1", "2")
    }
    assert outputs == {repr(build(AllTypes, seed=42))}


def test_empty_enum_raises_type_error_with_path() -> None:
    with pytest.raises(GenerationError) as exc:
        build(EmptyParent)
    assert str(exc.value) == (
        "cannot generate field 'EmptyParent.inner.kind' of type Empty: enum has no members. "
        "Add a member, or pass it as an override: build(EmptyParent, inner=...)"
    )
