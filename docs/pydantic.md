# Pydantic support

Install the extra:

```bash
pip install "polarfactory[pydantic]"
```

polarfactory never imports Pydantic itself. Pydantic support turns on when your
code has imported it.

```python
from pydantic import BaseModel, Field

from polarfactory import build


class Product(BaseModel):
    sku: str = Field(pattern=r"^[A-Z]{3}-\d{4}$")
    price: float = Field(gt=0, le=100)
    stock: int = Field(ge=0, lt=50)
    tags: list[str] = Field(min_length=2, max_length=4)


build(Product, seed=7)
# Product(sku='VSX-3536', price=93.32, stock=5,
#         tags=['slifysqc', 'fbkkaant', 'udpphwdy'])
```

Fields are read from `model_fields`, and models are created with
`model_validate`, so your validators run. Fields with an alias are generated and
overridden by their Python name.

## Constraints

| Constraint | Applies to |
|---|---|
| `ge`, `gt`, `le`, `lt` | `int`, `float`, `Decimal` |
| `min_length`, `max_length` | `str`, and the size of `list`, `set`, `dict`, `tuple[X, ...]` |
| `pattern` | `str` |

Patterns support literal characters, `.`, character classes like `[A-Z0-9]`,
`\d`, `\w`, `\s`, repeats (`{n}`, `{n,m}`, `+`, `*`, `?`), groups, alternatives
(`a|b`) and anchors. Other features, such as negated classes `[^a-z]`, raise a
`GenerationError` that asks you to pass the field as an override.

## Limits

- Pydantic special types such as `EmailStr` aren't generated yet. Pass them as
  overrides or use `register()`.
- `multiple_of` and other constraints not listed above are ignored.
- Overrides go through Pydantic validation, so a value of the wrong type fails
  or is converted.
- If validation fails, you get a `GenerationError` with Pydantic's details.
