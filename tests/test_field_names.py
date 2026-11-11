import re
from collections.abc import Iterator
from dataclasses import dataclass

import pytest

from polarfactory import build, register, reset_registry
from polarfactory._names import CITIES, COUNTRIES, FIRST_NAMES, LAST_NAMES

SEEDS = range(50)


@dataclass
class Profile:
    email: str
    name: str
    first_name: str
    last_name: str
    city: str
    country: str
    url: str
    phone: str
    username: str
    title: str
    description: str
    slug: str
    nickname: str


@dataclass
class Address:
    city: str


@dataclass
class Holder:
    address: Address
    email: str | None
    title: int


@pytest.fixture(autouse=True)
def clean_registry() -> Iterator[None]:
    yield
    reset_registry()


def check_profile(profile: Profile) -> None:
    assert re.fullmatch(r"[a-z]+\.[a-z]+\d{1,2}@example\.(com|org|net)", profile.email)
    first, last = profile.name.split(" ")
    assert first in FIRST_NAMES and last in LAST_NAMES
    assert profile.first_name in FIRST_NAMES and profile.last_name in LAST_NAMES
    assert profile.city in CITIES and profile.country in COUNTRIES
    assert re.fullmatch(r"https://example\.(com|org|net)/[a-z]+(-[a-z]+){1,3}", profile.url)
    assert re.fullmatch(r"\+1-555-01\d\d", profile.phone)
    assert re.fullmatch(r"[a-z]+_[a-z]+\d{1,3}", profile.username)
    assert re.fullmatch(r"[A-Z][a-z]+( [a-z]+){1,4}", profile.title)
    assert re.fullmatch(r"[A-Z][a-z]+( [a-z]+){7,14}\.", profile.description)
    assert re.fullmatch(r"[a-z]+(-[a-z]+){1,3}", profile.slug)


def test_known_field_names_get_realistic_values() -> None:
    for seed in SEEDS:
        check_profile(build(Profile, seed=seed))


def test_unknown_field_name_keeps_random_letters() -> None:
    assert re.fullmatch(r"[a-z]{8}", build(Profile, seed=1).nickname)


def test_same_seed_gives_same_values_and_seeds_vary() -> None:
    assert build(Profile, seed=3) == build(Profile, seed=3)
    assert len({build(Profile, seed=seed).name for seed in SEEDS}) > 10


def test_hint_uses_field_name_at_any_depth_and_inside_optional() -> None:
    for seed in SEEDS:
        holder = build(Holder, seed=seed)
        assert holder.address.city in CITIES
        assert holder.email is None or holder.email.endswith(
            ("example.com", "example.org", "example.net")
        )


def test_non_str_field_with_known_name_is_unchanged() -> None:
    assert type(build(Holder, seed=1).title) is int


def test_registered_str_generator_wins_over_field_names() -> None:
    register(str, lambda rng: "custom")
    assert build(Profile, seed=1).email == "custom"
