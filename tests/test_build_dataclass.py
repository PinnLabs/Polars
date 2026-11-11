from dataclasses import dataclass, field

import pytest

from polarfactory import build
from polarfactory.errors import GenerationError, PolarFactoryError


@dataclass
class User:
    id: int
    name: str
    active: bool


@dataclass
class WithDefaults:
    count: int = -1
    label: str = "default"
    flag: bool = False


@dataclass
class WithDerivedField:
    id: int
    derived: int = field(init=False, default=-1)


@dataclass
class Event:
    signal: complex


@dataclass
class Tagged:
    tags: dict[str, int]


class NotADataclass:
    pass


def test_builds_instance_with_exact_field_types() -> None:
    user = build(User)
    assert isinstance(user, User)
    assert type(user.id) is int
    assert type(user.name) is str
    assert type(user.active) is bool


def test_defaults_are_replaced_with_generated_values() -> None:
    built = build(WithDefaults)
    assert type(built.count) is int and built.count != -1
    assert type(built.label) is str and built.label != "default"
    assert type(built.flag) is bool
    # False is also a valid generated value, so check that True shows up too.
    assert any(build(WithDefaults).flag for _ in range(100))


def test_init_false_field_is_left_to_the_dataclass() -> None:
    built = build(WithDerivedField)
    assert type(built.id) is int
    assert built.derived == -1


@pytest.mark.parametrize(
    ("cls", "message"),
    [
        (
            Event,
            "cannot generate field 'Event.signal' of type complex. "
            "Pass it as an override: build(Event, signal=...)",
        ),
        (
            Tagged,
            "cannot generate field 'Tagged.tags' of type dict[str, int]. "
            "Pass it as an override: build(Tagged, tags=...)",
        ),
    ],
)
def test_unsupported_type_error_names_class_field_and_type(cls: type, message: str) -> None:
    with pytest.raises(GenerationError) as exc:
        build(cls)
    assert str(exc.value) == message


@pytest.mark.parametrize("value", [NotADataclass, User(1, "a", True)])
def test_non_dataclass_input_raises_type_error(value: object) -> None:
    with pytest.raises(PolarFactoryError) as exc:
        build(value)  # type: ignore[arg-type]
    assert str(exc.value) == (
        f"build() expects a dataclass or a class with __init__, got {value!r}"
    )
