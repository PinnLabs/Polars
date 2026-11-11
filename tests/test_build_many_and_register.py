import random
from collections.abc import Iterator
from dataclasses import dataclass

import pytest

from polarfactory import build, build_many, register, reset_registry
from polarfactory.errors import GenerationError, PolarFactoryError


@pytest.fixture(autouse=True)
def clean_registry() -> Iterator[None]:
    yield
    reset_registry()


@dataclass
class User:
    id: int
    name: str


@dataclass
class Signal:
    value: complex
    history: list[complex]
    backup: complex | None


def complex_from(rng: random.Random) -> complex:
    return complex(rng.randint(0, 9), rng.randint(0, 9))


def test_build_many_returns_n_distinct_items() -> None:
    users = build_many(User, 5, seed=1)
    assert len(users) == 5 and all(type(user) is User for user in users)
    assert len({repr(user) for user in users}) == 5


def test_build_many_same_seed_gives_same_list() -> None:
    assert build_many(User, 5, seed=1) == build_many(User, 5, seed=1)
    assert build_many(User, 5, seed=1) != build_many(User, 5, seed=2)


def test_build_many_without_seed_gives_different_lists() -> None:
    assert build_many(User, 3) != build_many(User, 3)


def test_build_many_applies_overrides_to_every_item() -> None:
    users = build_many(User, 3, seed=1, name="Ana")
    assert [user.name for user in users] == ["Ana"] * 3
    assert [user.id for user in users] == [user.id for user in build_many(User, 3, seed=1)]


def test_build_many_zero_gives_empty_list() -> None:
    assert build_many(User, 0) == []


@pytest.mark.parametrize(
    ("call", "message"),
    [
        (lambda: build_many(User, -1), "build_many() expects n >= 0, got -1"),
        (
            lambda: build_many(User, 2, nmae="x"),
            "build_many() got unknown field 'nmae' for User; valid fields: id, name",
        ),
        (
            lambda: register(complex, "not callable"),  # type: ignore[arg-type]
            "register() expects a callable for <class 'complex'>, got 'not callable'",
        ),
    ],
    ids=["negative-n", "unknown-override", "not-callable"],
)
def test_argument_errors(call: object, message: str) -> None:
    with pytest.raises(PolarFactoryError) as exc:
        call()  # type: ignore[operator]
    assert str(exc.value) == message


def test_registered_generator_gets_rng_and_is_deterministic() -> None:
    received = []

    def generate(rng: random.Random) -> complex:
        received.append(rng)
        return complex_from(rng)

    register(complex, generate)
    assert build(Signal, seed=3) == build(Signal, seed=3)
    assert received and all(type(rng) is random.Random for rng in received)


def test_registered_type_works_inside_list_and_optional() -> None:
    register(complex, complex_from)
    for seed in range(20):
        signal = build(Signal, seed=seed)
        assert type(signal.value) is complex
        assert signal.history and all(type(item) is complex for item in signal.history)
        assert signal.backup is None or type(signal.backup) is complex


def test_registered_generator_replaces_builtin_one() -> None:
    register(str, lambda rng: "fixed")
    assert build(User).name == "fixed"


def test_reset_registry_restores_defaults() -> None:
    register(str, lambda rng: "fixed")
    register(complex, complex_from)
    reset_registry()
    assert build(User).name != "fixed"
    with pytest.raises(GenerationError, match="Signal.value"):
        build(Signal)
