from dataclasses import dataclass
from typing import Any, Optional

import pytest

from polarfactory import build


@dataclass
class Address:
    city: str


class Person:
    def __init__(self, name: str, address: Address, backup: Optional[Address] = None) -> None:  # noqa: UP045
        self.name = name
        self.address = address
        self.backup = backup

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Person) and vars(self) == vars(other)


class Team:
    def __init__(self, lead: Person, members: list[Person], *args: Any, **kwargs: Any) -> None:
        self.lead = lead
        self.members = members
        self.extra = (args, kwargs)


class Untyped:
    def __init__(self, id: int, label) -> None:  # type: ignore[no-untyped-def]
        self.id = id
        self.label = label


@dataclass
class HoldsUntyped:
    inner: Untyped


class Node:
    def __init__(self, value: int, children: "list[Node]") -> None:
        self.value = value
        self.children = children


def test_plain_class_with_nested_dataclass_builds_deterministically() -> None:
    person = build(Person, seed=3)
    assert type(person.name) is str
    assert type(person.address) is Address and type(person.address.city) is str
    assert person == build(Person, seed=3)
    assert person != build(Person, seed=4)


def test_plain_classes_nest_inside_each_other_and_skip_varargs() -> None:
    team = build(Team, seed=1)
    assert type(team.lead) is Person
    assert team.members and all(type(member) is Person for member in team.members)
    assert team.extra == ((), {})


def test_overrides_and_unknown_field_error() -> None:
    plain = build(Person, seed=1)
    overridden = build(Person, seed=1, name="Ana")
    assert overridden.name == "Ana" and overridden.address == plain.address
    with pytest.raises(TypeError) as exc:
        build(Person, nmae="x")
    assert str(exc.value) == (
        "build() got unknown field 'nmae' for Person; valid fields: name, address, backup"
    )


def test_missing_type_hint_raises_naming_the_parameter() -> None:
    message = "parameter 'label' of Untyped.__init__ has no type hint"
    with pytest.raises(TypeError, match=message):
        build(Untyped)
    with pytest.raises(TypeError, match=f"'HoldsUntyped.inner.label': {message}"):
        build(HoldsUntyped)


def test_self_reference_stops_at_max_depth() -> None:
    node = build(Node, seed=1)
    assert type(node.value) is int and all(type(child) is Node for child in node.children)
