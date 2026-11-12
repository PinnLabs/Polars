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


user = build(User, seed=42)
# User(id=8753, name='Grace Rossi', email='mateo.brown2@example.org',
#      created=datetime.datetime(2022, 3, 4, 1, 29, 27, tzinfo=datetime.timezone.utc),
#      address=Address(city='Toronto', country='Nigeria'),
#      tags=['hwnoekxw', 'lucfvluc', 'pxxscfvm'], nickname='dpsjyett')

build(User, seed=42, name="Ana")  # same values, except name
build_many(User, 3, seed=1)  # three different users, same list every run
```

- Same seed, same object, in every process.
- Works with dataclasses, plain classes and Pydantic v2 models, including
  nested ones.
- Field names like `email`, `name` or `city` get realistic values.
- Errors say how to fix the problem.

Full documentation: <https://pinnlabs.github.io/Polars/>

## License

MIT
