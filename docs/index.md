# polarfactory

Generate Python objects filled with realistic test data, from the type hints you
already have.

```bash
pip install polarfactory
pip install "polarfactory[pydantic]"  # optional: Pydantic v2 support
```

## Quickstart

```python
from dataclasses import dataclass
from datetime import datetime

from polarfactory import build, build_many


@dataclass
class Address:
    city: str
    country: str


@dataclass
class User:
    id: int
    name: str
    email: str
    created: datetime
    address: Address
    tags: list[str]
    nickname: str | None


build(User, seed=42)
# User(id=8753, name='Grace Rossi', email='mateo.brown2@example.org',
#      created=datetime.datetime(2022, 3, 4, 1, 29, 27, tzinfo=datetime.timezone.utc),
#      address=Address(city='Toronto', country='Nigeria'),
#      tags=['hwnoekxw', 'lucfvluc', 'pxxscfvm'], nickname='dpsjyett')
```

Every field is generated from its type hint. Nested classes are built too.

## Why polarfactory

- **Deterministic.** The same seed gives the same object, in every process.
  Each field has its own random stream, so adding a field or overriding one
  doesn't change the others.
- **No setup.** No factory classes to write. Pass the class you already have.
- **Realistic where it matters.** Fields named `email`, `name`, `city` and
  similar get values that look real.
- **Clear errors.** When something can't be generated, the message says how to
  fix it.

Next: the [user guide](guide.md) and [Pydantic support](pydantic.md).
