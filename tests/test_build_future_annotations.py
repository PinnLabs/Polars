from __future__ import annotations

from dataclasses import dataclass

from polarfactory import build


@dataclass
class User:
    id: int
    name: str
    active: bool


def test_string_annotations_are_resolved() -> None:
    user = build(User)
    assert type(user.id) is int
    assert type(user.name) is str
    assert type(user.active) is bool
