import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Optional

import pytest

pydantic = pytest.importorskip("pydantic")

from pydantic import BaseModel, Field, field_validator  # noqa: E402

from polarfactory import build, build_many, register, reset_registry  # noqa: E402
from polarfactory.errors import GenerationError, PolarFactoryError  # noqa: E402

SEEDS = range(100)


@dataclass
class Geo:
    lat: int


class Address(BaseModel):
    city: str
    geo: Geo


class User(BaseModel):
    id: int
    name: str
    address: Address
    tags: list[str]
    nickname: str | None


class Bounds(BaseModel):
    age: int = Field(ge=18, le=65)
    score: int = Field(gt=0, lt=5)
    debt: int = Field(le=-5)
    big: int = Field(ge=1_000_000)
    ratio: float = Field(gt=0, lt=1)
    price: Decimal = Field(ge=Decimal("9.99"), le=Decimal("10.01"))
    maybe: Optional[int] = Field(default=None, gt=100)  # noqa: UP045


class Lengths(BaseModel):
    code: str = Field(min_length=12, max_length=12)
    name: str = Field(max_length=3)
    short: str = Field(min_length=1, max_length=2)
    items: list[int] = Field(min_length=4, max_length=6)
    exact: set[int] = Field(min_length=1, max_length=1)


class Patterns(BaseModel):
    sku: str = Field(pattern=r"^[A-Z]{3}-\d{4}$")
    kind: str = Field(pattern=r"^(foo|bar)_\w+$")
    loose: str = Field(pattern=r"^a.b?c*x+$")
    nested: str = Field(pattern=r"^(ab|c[0-9]{2})+$")


class Aliased(BaseModel):
    user_id: int = Field(alias="userId")


class Impossible(BaseModel):
    value: int = Field(ge=5, le=4)


class NegatedPattern(BaseModel):
    code: str = Field(pattern=r"^[^ab]+$")


class Picky(BaseModel):
    id: int

    @field_validator("id")
    @classmethod
    def reject(cls, value: int) -> int:
        raise ValueError("never valid")


@pytest.fixture(autouse=True)
def clean_registry() -> Any:
    yield
    reset_registry()


def test_model_with_nested_model_and_dataclass() -> None:
    user = build(User, seed=1)
    assert type(user) is User and type(user.id) is int
    assert type(user.address) is Address and type(user.address.geo) is Geo
    assert user.tags and all(type(tag) is str for tag in user.tags)
    assert user.address.city.istitle()  # field-name hints still apply


def test_same_seed_gives_equal_model() -> None:
    assert build(User, seed=3) == build(User, seed=3)
    assert build_many(User, 3, seed=3) == build_many(User, 3, seed=3)


def test_numeric_bounds_are_respected() -> None:
    values = [build(Bounds, seed=seed) for seed in SEEDS]
    for item in values:
        assert 18 <= item.age <= 65 and 0 < item.score < 5
        assert item.debt <= -5 and item.big >= 1_000_000
        assert 0 < item.ratio < 1
        assert type(item.price) is Decimal and Decimal("9.99") <= item.price <= Decimal("10.01")
        assert item.maybe is None or item.maybe > 100
    assert {item.score for item in values} == {1, 2, 3, 4}


def test_lengths_are_respected() -> None:
    for seed in SEEDS:
        item = build(Lengths, seed=seed)
        assert len(item.code) == 12 and len(item.name) <= 3 and 1 <= len(item.short) <= 2
        assert 4 <= len(item.items) <= 6 and len(item.exact) == 1


@pytest.mark.parametrize("field", ["sku", "kind", "loose", "nested"])
def test_generated_strings_match_basic_patterns(field: str) -> None:
    pattern = Patterns.model_fields[field].metadata[0].pattern
    values = {getattr(build(Patterns, seed=seed), field) for seed in SEEDS}
    assert all(re.fullmatch(pattern, value) for value in values)
    assert len(values) > 10


def test_alias_field_is_built_and_overridden_by_name() -> None:
    assert type(build(Aliased, seed=1).user_id) is int
    assert build(Aliased, user_id=7).user_id == 7


def test_overrides_and_unknown_field() -> None:
    assert build(User, seed=1, name="Ana").address == build(User, seed=1).address
    with pytest.raises(PolarFactoryError) as exc:
        build(User, nmae="x")
    assert str(exc.value) == (
        "build() got unknown field 'nmae' for User; valid fields: id, name, address, tags, nickname"
    )


def test_registered_generator_is_used_for_model_fields() -> None:
    register(str, lambda rng: "custom")
    assert build(User, seed=1).name == "custom"


@pytest.mark.parametrize(
    ("cls", "message"),
    [
        (
            Impossible,
            "cannot generate field 'Impossible.value' with ge=5, le=4: no int fits these "
            "bounds. Pass it as an override: build(Impossible, value=...)",
        ),
        (
            NegatedPattern,
            "cannot generate field 'NegatedPattern.code' with pattern='^[^ab]+$': pattern "
            "'^[^ab]+$' uses unsupported regex feature negate. "
            "Pass it as an override: build(NegatedPattern, code=...)",
        ),
    ],
    ids=["impossible-bounds", "unsupported-pattern"],
)
def test_constraint_errors(cls: type, message: str) -> None:
    with pytest.raises(GenerationError) as exc:
        build(cls)
    assert str(exc.value) == message


def test_failed_validation_raises_generation_error() -> None:
    with pytest.raises(GenerationError) as exc:
        build(Picky)
    assert str(exc.value).startswith(
        "values for 'Picky' failed Picky validation. Pass the failing fields as overrides. "
        "Details:\n"
    )
    assert "never valid" in str(exc.value)
