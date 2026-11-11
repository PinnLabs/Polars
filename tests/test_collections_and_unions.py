from dataclasses import dataclass
from typing import Any, Literal, Optional, Union

import pytest

from polarfactory import build
from polarfactory.errors import GenerationError

SEEDS = range(100)


@dataclass
class Address:
    city: str


@dataclass
class Collections:
    scores: dict[str, int]
    addresses: dict[int, Address]
    tags: set[str]
    pair: tuple[int, str]
    many: tuple[float, ...]
    nested: list[dict[str, set[int]]]


@dataclass
class Unions:
    value: int | str
    old_style: Union[int, Address]  # noqa: UP007
    maybe: int | str | None
    old_maybe: Optional[Union[int, str]]  # noqa: UP007, UP045


@dataclass
class Tree:
    value: int
    child: "Tree | int"


@dataclass
class Bad:
    value: complex | int


@dataclass
class UnhashableSet:
    items: set[list[int]]


@dataclass
class UnhashableKeys:
    items: dict[list[int], int]


@dataclass
class BareDict:
    items: dict  # type: ignore[type-arg]


@dataclass
class BareSet:
    items: set  # type: ignore[type-arg]


@dataclass
class BareTuple:
    items: tuple  # type: ignore[type-arg]


def all_type(values: Any, expected: type) -> bool:
    return all(type(value) is expected for value in values)


def test_collections_have_right_types_and_sizes() -> None:
    for seed in SEEDS:
        built = build(Collections, seed=seed)
        assert type(built.scores) is dict and 1 <= len(built.scores) <= 3
        assert all_type(built.scores, str) and all_type(built.scores.values(), int)
        assert all_type(built.addresses, int) and all_type(built.addresses.values(), Address)
        assert type(built.tags) is set and 1 <= len(built.tags) <= 3
        assert all_type(built.tags, str)
        assert type(built.pair) is tuple and len(built.pair) == 2
        assert type(built.pair[0]) is int and type(built.pair[1]) is str
        assert type(built.many) is tuple and 1 <= len(built.many) <= 3
        assert all_type(built.many, float)
        for mapping in built.nested:
            assert all_type(mapping, str)
            assert all(all_type(numbers, int) for numbers in mapping.values())


def test_variable_sizes_cover_the_whole_range() -> None:
    built = [build(Collections, seed=seed) for seed in SEEDS]
    assert {len(item.scores) for item in built} == {1, 2, 3}
    assert {len(item.many) for item in built} == {1, 2, 3}


def test_unions_pick_every_member_across_seeds() -> None:
    built = [build(Unions, seed=seed) for seed in SEEDS]
    assert {type(item.value) for item in built} == {int, str}
    assert {type(item.old_style) for item in built} == {int, Address}
    assert {type(item.maybe) for item in built} == {int, str, type(None)}
    assert {type(item.old_maybe) for item in built} == {int, str, type(None)}


def test_union_with_literal_picks_from_both() -> None:
    model = dataclass(type("Model", (), {"__annotations__": {"value": Literal["a"] | int}}))
    assert {type(build(model, seed=seed).value) for seed in SEEDS} == {str, int}


def test_same_seed_gives_equal_object() -> None:
    assert build(Collections, seed=7) == build(Collections, seed=7)
    assert build(Unions, seed=7) == build(Unions, seed=7)


def test_recursive_union_falls_back_to_other_member_at_max_depth() -> None:
    for seed in range(20):
        node: Tree | int = build(Tree, seed=seed)
        depth = 0
        while isinstance(node, Tree):
            node, depth = node.child, depth + 1
        assert type(node) is int and depth <= 4


def test_unsupported_union_member_raises_for_every_seed() -> None:
    for seed in range(20):
        with pytest.raises(GenerationError) as exc:
            build(Bad, seed=seed)
        assert str(exc.value) == (
            "cannot generate field 'Bad.value' of type complex. "
            "Pass it as an override: build(Bad, value=...)"
        )


@pytest.mark.parametrize(
    ("cls", "message"),
    [
        (
            UnhashableSet,
            "cannot generate field 'UnhashableSet.items' of type set[list[int]]: items are not "
            "hashable. Use a hashable type, or pass it as an override: "
            "build(UnhashableSet, items=...)",
        ),
        (
            UnhashableKeys,
            "cannot generate field 'UnhashableKeys.items' of type dict[list[int], int]: keys are "
            "not hashable. Use a hashable type, or pass it as an override: "
            "build(UnhashableKeys, items=...)",
        ),
        (
            BareDict,
            "cannot generate field 'BareDict.items' of type dict. "
            "Use dict[K, V], or pass it as an override: build(BareDict, items=...)",
        ),
        (
            BareSet,
            "cannot generate field 'BareSet.items' of type set. "
            "Use set[X], or pass it as an override: build(BareSet, items=...)",
        ),
        (
            BareTuple,
            "cannot generate field 'BareTuple.items' of type tuple. "
            "Use tuple[X, Y] or tuple[X, ...], or pass it as an override: "
            "build(BareTuple, items=...)",
        ),
    ],
    ids=["unhashable-set", "unhashable-keys", "bare-dict", "bare-set", "bare-tuple"],
)
def test_error_messages(cls: type, message: str) -> None:
    with pytest.raises(GenerationError) as exc:
        build(cls)
    assert str(exc.value) == message
