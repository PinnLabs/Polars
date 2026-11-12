# User guide

## Seeds and overrides

```python
build(User)  # random values, different every call
build(User, seed=42)  # the same object every time
build(User, seed=42, name="Ana")  # same values, except name
```

Overrides are used exactly as given and are never generated, so they also work
for fields whose type polarfactory can't generate. Only top-level fields can be
overridden.

## Many objects

```python
users = build_many(User, 3, seed=1)
[user.name for user in users]
# ['Carla Silva', 'Ana Novak', 'Rosa Johansson']
```

Items differ from each other, and the same seed gives the same list. Overrides
apply to every item.

## Supported classes

- **Dataclasses.** `InitVar` fields are generated and passed to `__post_init__`.
  `init=False` fields are left to the dataclass.
- **Plain classes.** Fields come from the `__init__` signature and its type
  hints. `*args` and `**kwargs` are skipped.
- **Pydantic v2 models.** See [Pydantic support](pydantic.md).

## Supported types

| Type | Generated value |
|---|---|
| `int` | 0 to 10,000 |
| `float` | 0 to 10,000, two decimals |
| `Decimal` | 0 to 10,000, two decimals |
| `bool` | `True` or `False` |
| `str` | 8 lowercase letters, or a realistic value for [known field names](#realistic-values-from-field-names) |
| `bytes` | 8 random bytes |
| `datetime`, `date` | within the 5 years before 2025-01-01, `datetime` in UTC |
| `time`, `timedelta` | any time of day; up to 30 days |
| `UUID` | version 4 |
| `Enum`, `Literal[...]` | one of the members |
| `list[X]`, `set[X]`, `tuple[X, ...]` | 1 to 3 items |
| `dict[K, V]` | 1 to 3 entries |
| `tuple[X, Y]` | one value per position |
| `X | None`, `Optional[X]` | `None` about a quarter of the time |
| `X | Y`, `Union[X, Y]` | one member, picked by the seed |

Classes can refer to themselves, like a tree. Recursion stops after 3 levels:
optional fields become `None`, collections become empty, and a union picks
another member.

## Realistic values from field names

`str` fields with these exact names get realistic values:

| Field name | Example |
|---|---|
| `name`, `first_name`, `last_name` | `Grace Rossi`, `Grace`, `Rossi` |
| `email` | `mateo.brown2@example.org` |
| `username` | `kenji_timber204` |
| `city`, `country` | `Toronto`, `Nigeria` |
| `url` | `https://example.org/ocean-field` |
| `phone` | `+1-555-0136` |
| `title`, `description`, `slug` | `Willow silver urban bright`, a sentence, `velvet-spark-yellow` |

Emails and URLs only use the reserved `example.com`, `example.org` and
`example.net` domains, and phone numbers use the fictional 555-01xx range, so
generated data never reaches a real person.

## Custom types

Register a generator for any type. It receives a seeded `random.Random`, so
results stay deterministic:

```python
from ipaddress import IPv4Address

from polarfactory import register, reset_registry

register(IPv4Address, lambda rng: IPv4Address(rng.getrandbits(32)))
```

A registered generator also wins over the built-in one, so `register(str, ...)`
replaces the default strings. The registry is global; reset it between tests:

```python
import pytest


@pytest.fixture(autouse=True)
def clean_registry():
    yield
    reset_registry()
```

## Errors

All errors subclass `TypeError`, so existing `except TypeError` code keeps
working:

- `polarfactory.errors.PolarFactoryError`: wrong arguments to `build()` or
  `build_many()`, such as an unknown override.
- `polarfactory.errors.GenerationError`: a field value can't be generated.

Every message says how to fix the problem:

```python
@dataclass
class Order:
    total: complex


build(Order)
# GenerationError: cannot generate field 'Order.total' of type complex.
# Pass it as an override: build(Order, total=...)
```
