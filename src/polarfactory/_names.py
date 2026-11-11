"""Realistic str values picked from the field name, e.g. a field called `email` gets an email."""

import random
from collections.abc import Callable

FIRST_NAMES = (
    "Ana", "Bruno", "Carla", "David", "Elena", "Fatima", "Grace", "Hiro", "Isabel", "James",
    "Kenji", "Laura", "Mateo", "Nadia", "Omar", "Priya", "Quentin", "Rosa", "Samuel", "Tara",
)  # fmt: skip
LAST_NAMES = (
    "Silva", "Smith", "Garcia", "Kim", "Müller", "Rossi", "Nguyen", "Okafor", "Costa", "Tanaka",
    "Novak", "Haddad", "Johansson", "Patel", "Dubois", "Moreno", "Kowalski", "Ali", "Brown", "Lee",
)  # fmt: skip
CITIES = (
    "Lisbon", "São Paulo", "Tokyo", "Nairobi", "Berlin", "Toronto", "Mumbai", "Sydney",
    "Mexico City", "Seoul", "Cairo", "Paris", "Buenos Aires", "Oslo", "Lagos",
)  # fmt: skip
COUNTRIES = (
    "Portugal", "Brazil", "Japan", "Kenya", "Germany", "Canada", "India", "Australia",
    "Mexico", "South Korea", "Egypt", "France", "Argentina", "Norway", "Nigeria",
)  # fmt: skip
WORDS = (
    "amber", "bright", "cloud", "delta", "echo", "field", "garden", "harbor", "island", "jade",
    "kite", "lemon", "maple", "north", "ocean", "pixel", "quiet", "river", "silver", "timber",
    "urban", "velvet", "willow", "yellow", "zephyr", "stone", "spark", "meadow", "copper", "light",
)  # fmt: skip
# Reserved for documentation (RFC 2606), so generated addresses never reach a real inbox.
DOMAINS = ("example.com", "example.org", "example.net")


def _ascii(text: str) -> str:
    return text.lower().replace("ü", "u").replace(" ", "")


def _first_name(rng: random.Random) -> str:
    return rng.choice(FIRST_NAMES)


def _last_name(rng: random.Random) -> str:
    return rng.choice(LAST_NAMES)


def _name(rng: random.Random) -> str:
    return f"{_first_name(rng)} {_last_name(rng)}"


def _email(rng: random.Random) -> str:
    first, last = _ascii(_first_name(rng)), _ascii(_last_name(rng))
    return f"{first}.{last}{rng.randint(1, 99)}@{rng.choice(DOMAINS)}"


def _username(rng: random.Random) -> str:
    return f"{_ascii(_first_name(rng))}_{rng.choice(WORDS)}{rng.randint(1, 999)}"


def _words(rng: random.Random, low: int, high: int) -> list[str]:
    return [rng.choice(WORDS) for _ in range(rng.randint(low, high))]


def _slug(rng: random.Random) -> str:
    return "-".join(_words(rng, 2, 4))


def _url(rng: random.Random) -> str:
    return f"https://{rng.choice(DOMAINS)}/{_slug(rng)}"


def _phone(rng: random.Random) -> str:
    # 555-0100 to 555-0199 is reserved for fiction, so no real person gets called.
    return f"+1-555-01{rng.randint(0, 99):02d}"


def _title(rng: random.Random) -> str:
    return " ".join(_words(rng, 2, 5)).capitalize()


def _description(rng: random.Random) -> str:
    return " ".join(_words(rng, 8, 15)).capitalize() + "."


NAME_GENERATORS: dict[str, Callable[[random.Random], str]] = {
    "email": _email,
    "name": _name,
    "first_name": _first_name,
    "last_name": _last_name,
    "city": lambda rng: rng.choice(CITIES),
    "country": lambda rng: rng.choice(COUNTRIES),
    "url": _url,
    "phone": _phone,
    "username": _username,
    "title": _title,
    "description": _description,
    "slug": _slug,
}
