from dataclasses import dataclass
from typing import Optional

import pytest

from polarfactory import build
from polarfactory.errors import GenerationError

SEEDS = range(200)


@dataclass
class Geo:
    lat: int


@dataclass
class Address:
    city: str
    geo: Geo


@dataclass
class User:
    name: str
    address: Address


@dataclass
class Lists:
    tags: list[str]
    addresses: list[Address]
    grid: list[list[int]]


@dataclass
class Optionals:
    nickname: str | None
    backup: Optional[Address]  # noqa: UP045


@dataclass
class WithExtraField:
    extra: int
    name: str
    address: Address


@dataclass
class Node:
    value: int
    children: list["Node"]


@dataclass
class Chain:
    next: Optional["Chain"]  # noqa: UP045


@dataclass
class Parent:
    child: "Child"


@dataclass
class Child:
    parent: Parent | None


@dataclass
class Loop:
    next: "Loop"


@dataclass
class Level4:
    value: int


@dataclass
class Level3:
    child: Level4


@dataclass
class Level2:
    child: Level3


@dataclass
class Level1:
    child: Level2


@dataclass
class Level0:
    child: Level1


@dataclass
class DeepBadAddress:
    signal: complex


@dataclass
class DeepBad:
    address: DeepBadAddress


@dataclass
class BadInList:
    items: list[DeepBadAddress]


@dataclass
class BadInOptional:
    signal: complex | None


@dataclass
class BareList:
    items: list


@dataclass
class OtherUnion:
    value: int | str | None


def node_depth(node: Node) -> int:
    return 1 + max((node_depth(child) for child in node.children), default=-1)


def chain_depth(chain: Chain) -> int:
    return 0 if chain.next is None else 1 + chain_depth(chain.next)


def test_nested_dataclass_has_right_types_at_every_level() -> None:
    user = build(User)
    assert type(user.name) is str
    assert type(user.address) is Address
    assert type(user.address.city) is str
    assert type(user.address.geo) is Geo
    assert type(user.address.geo.lat) is int


def test_lists_have_one_to_three_items_of_the_right_type() -> None:
    for seed in SEEDS:
        built = build(Lists, seed=seed)
        for items in (built.tags, built.addresses, built.grid):
            assert 1 <= len(items) <= 3
        assert all(type(tag) is str for tag in built.tags)
        assert all(type(address) is Address for address in built.addresses)
        for row in built.grid:
            assert 1 <= len(row) <= 3
            assert all(type(cell) is int for cell in row)


def test_list_lengths_cover_the_whole_range() -> None:
    assert {len(build(Lists, seed=seed).tags) for seed in SEEDS} == {1, 2, 3}


def test_optional_gives_about_a_quarter_none_for_both_spellings() -> None:
    built = [build(Optionals, seed=seed) for seed in SEEDS]
    for values, value_type in (
        ([item.nickname for item in built], str),
        ([item.backup for item in built], Address),
    ):
        values_without_none = [value for value in values if value is not None]
        assert all(type(value) is value_type for value in values_without_none)
        # Seeds are fixed, so this range can't be flaky.
        assert 0.15 < 1 - len(values_without_none) / len(values) < 0.35


def test_same_seed_gives_equal_nested_tree() -> None:
    assert build(Lists, seed=7) == build(Lists, seed=7)
    assert build(Optionals, seed=7) == build(Optionals, seed=7)
    assert build(Node, seed=7) == build(Node, seed=7)


def test_unrelated_fields_do_not_shift_nested_values() -> None:
    plain = build(User, seed=1)
    assert build(WithExtraField, seed=1).address == plain.address
    assert build(User, seed=1, name="Ana").address == plain.address


def test_self_referencing_list_stops_at_max_depth() -> None:
    assert {node_depth(build(Node, seed=seed)) for seed in range(20)} == {3}


def test_self_referencing_optional_stops_at_max_depth() -> None:
    assert max(chain_depth(build(Chain, seed=seed)) for seed in SEEDS) == 3


def test_mutual_recursion_terminates_through_its_optional_field() -> None:
    assert type(build(Parent, seed=1).child) is Child


def test_required_self_reference_raises_with_path() -> None:
    with pytest.raises(TypeError) as exc:
        build(Loop)
    assert str(exc.value) == (
        "cannot generate field 'Loop.next.next.next.next' of type Loop: "
        "required self-reference exceeds max depth 3. "
        "Make it Optional or a list, or pass it as an override: build(Loop, next=...)"
    )


def test_required_self_reference_can_be_overridden() -> None:
    assert build(Loop, next=None).next is None


def test_max_depth_does_not_limit_nesting_without_recursion() -> None:
    assert type(build(Level0).child.child.child.child.value) is int


@pytest.mark.parametrize(
    ("cls", "path"),
    [
        (DeepBad, "DeepBad.address.signal"),
        (BadInList, "BadInList.items.signal"),
    ],
)
def test_unsupported_type_deep_inside_shows_full_path(cls: type, path: str) -> None:
    with pytest.raises(GenerationError) as exc:
        build(cls)
    root, field = path.split(".")[:2]
    assert str(exc.value) == (
        f"cannot generate field '{path}' of type complex. "
        f"Pass it as an override: build({root}, {field}=...)"
    )


def test_unsupported_type_inside_optional_raises_for_every_seed() -> None:
    # Must not depend on whether the seed happens to roll None.
    for seed in range(20):
        with pytest.raises(TypeError, match="BadInOptional.signal"):
            build(BadInOptional, seed=seed)


def test_bare_list_raises_type_error_asking_for_item_type() -> None:
    with pytest.raises(TypeError) as exc:
        build(BareList)
    assert str(exc.value) == (
        "cannot generate field 'BareList.items' of type list. "
        "Use list[X], or pass it as an override: build(BareList, items=...)"
    )


def test_other_unions_stay_unsupported() -> None:
    with pytest.raises(TypeError, match="OtherUnion.value"):
        build(OtherUnion)
