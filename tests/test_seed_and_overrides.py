import os
import subprocess
import sys
from dataclasses import dataclass, field

import pytest

from polarfactory import build


@dataclass
class User:
    id: int
    name: str
    active: bool


@dataclass
class Event:
    signal: complex
    derived: int = field(init=False, default=-1)


SCRIPT = """
from dataclasses import dataclass
from polarfactory import build

@dataclass
class User:
    id: int
    name: str
    active: bool

print(repr(build(User, seed=42)))
"""


@pytest.mark.parametrize("seed", [0, 42])
def test_same_seed_gives_equal_objects(seed: int) -> None:
    assert build(User, seed=seed) == build(User, seed=seed)


def test_different_seeds_give_different_objects() -> None:
    assert len({repr(build(User, seed=seed)) for seed in range(10)}) > 1


def test_no_seed_gives_different_objects() -> None:
    assert len({repr(build(User)) for _ in range(10)}) > 1


def test_same_seed_gives_same_result_in_separate_processes() -> None:
    outputs = {
        subprocess.run(
            [sys.executable, "-c", SCRIPT],
            env={**os.environ, "PYTHONHASHSEED": hash_seed},
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        for hash_seed in ("1", "2")
    }
    assert outputs == {repr(build(User, seed=42))}


def test_override_is_used_exactly_as_given() -> None:
    assert build(User, name="Ana").name == "Ana"
    assert build(User, id="not an int").id == "not an int"


def test_override_of_unsupported_type_is_not_generated() -> None:
    value = complex(1, 2)
    assert build(Event, signal=value).signal is value


def test_override_leaves_other_fields_unchanged_for_same_seed() -> None:
    plain = build(User, seed=1)
    overridden = build(User, seed=1, name="Ana")
    assert overridden == User(plain.id, "Ana", plain.active)


def test_unknown_override_lists_only_settable_fields() -> None:
    with pytest.raises(TypeError) as exc:
        build(Event, nmae="x")
    assert str(exc.value) == "build() got unknown field 'nmae' for Event; valid fields: signal"


def test_override_of_init_false_field_raises_type_error() -> None:
    with pytest.raises(TypeError) as exc:
        build(Event, derived=1)
    assert str(exc.value) == (
        "build() cannot set field 'Event.derived': it has init=False. "
        "Set it on the built object instead"
    )
