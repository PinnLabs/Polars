"""Value generation under field constraints (bounds, lengths, regex patterns)."""

import dataclasses
import importlib
import math
import random
import string
import sys
from decimal import Decimal
from typing import Any

# shortcut: the stdlib regex parser is private API (sre_parse, renamed re._parser in 3.11).
# Replace it with a small own parser if a Python release changes its token format.
sre_parse: Any = importlib.import_module(
    "re._parser" if sys.version_info >= (3, 11) else "sre_parse"
)

_NAMES = ("ge", "gt", "le", "lt", "min_length", "max_length", "pattern")
_SPAN = 10_000
_UNBOUNDED_REPEAT = 3
_CATEGORIES = {
    sre_parse.CATEGORY_DIGIT: string.digits,
    sre_parse.CATEGORY_WORD: string.ascii_letters + string.digits + "_",
    sre_parse.CATEGORY_SPACE: " ",
}
_ANY_CHAR = string.ascii_letters + string.digits


@dataclasses.dataclass(frozen=True)
class Constraints:
    ge: Any = None
    gt: Any = None
    le: Any = None
    lt: Any = None
    min_length: int | None = None
    max_length: int | None = None
    pattern: str | None = None

    @classmethod
    def from_metadata(cls, metadata: list[Any]) -> "Constraints | None":
        # Duck-typed so annotated_types and pydantic metadata work without importing either.
        found = {
            name: getattr(item, name)
            for item in metadata
            for name in _NAMES
            if getattr(item, name, None) is not None
        }
        return cls(**found) if found else None

    def size_range(self, low: int, high: int) -> tuple[int, int]:
        lo = self.min_length if self.min_length is not None else low
        hi = self.max_length if self.max_length is not None else max(lo, high)
        return min(lo, hi), hi


class UnsupportedConstraint(ValueError):
    pass


def generate_number(tp: type, constraints: Constraints, rng: random.Random) -> Any:
    step = 1.0 if tp is int else 0.01
    lo = _bound(constraints.ge, constraints.gt, step)
    hi = _bound(constraints.le, constraints.lt, -step)
    if lo is None and hi is None:
        lo, hi = 0.0, float(_SPAN)
    elif lo is None:
        lo = hi - _SPAN if hi < 0 else 0.0  # type: ignore[operator]
    elif hi is None:
        hi = max(lo, 0.0) + _SPAN
    assert lo is not None and hi is not None
    if tp is int:
        low, high = math.ceil(lo), math.floor(hi)
        if low > high:
            raise UnsupportedConstraint("no int fits these bounds")
        return rng.randint(low, high)
    if lo > hi:
        raise UnsupportedConstraint("no number fits these bounds")
    value = min(max(round(rng.uniform(lo, hi), 2), lo), hi)
    return Decimal(str(value)) if tp is Decimal else value


def _bound(inclusive: Any, exclusive: Any, step: float) -> float | None:
    if inclusive is not None:
        return float(inclusive)
    if exclusive is not None:
        return float(exclusive) + step
    return None


def describe(constraints: Constraints) -> str:
    return ", ".join(
        f"{field.name}={getattr(constraints, field.name)!r}"
        for field in dataclasses.fields(constraints)
        if getattr(constraints, field.name) is not None
    )


def fit_length(value: str, constraints: Constraints, rng: random.Random) -> str:
    lo, hi = constraints.size_range(0, max(len(value), 8))
    if lo <= len(value) <= hi:
        return value
    return "".join(rng.choices(string.ascii_lowercase, k=rng.randint(lo, hi)))


def generate_from_pattern(pattern: str, rng: random.Random) -> str:
    try:
        return _emit(sre_parse.parse(pattern), rng)
    except UnsupportedConstraint as exc:
        raise UnsupportedConstraint(f"pattern {pattern!r} uses {exc}") from exc


def _emit(items: Any, rng: random.Random) -> str:
    out = []
    for op, arg in items:
        if op is sre_parse.LITERAL:
            out.append(chr(arg))
        elif op is sre_parse.ANY:
            out.append(rng.choice(_ANY_CHAR))
        elif op is sre_parse.IN:
            out.append(rng.choice(_charset(arg)))
        elif op is sre_parse.CATEGORY:
            out.append(rng.choice(_category(arg)))
        elif op in (sre_parse.MAX_REPEAT, sre_parse.MIN_REPEAT):
            low, high, sub = arg
            high = low + _UNBOUNDED_REPEAT if high is sre_parse.MAXREPEAT else high
            out.extend(_emit(sub, rng) for _ in range(rng.randint(low, high)))
        elif op is sre_parse.SUBPATTERN:
            out.append(_emit(arg[-1], rng))
        elif op is sre_parse.BRANCH:
            out.append(_emit(rng.choice(arg[1]), rng))
        elif op is not sre_parse.AT:  # anchors like ^ and $ produce no characters
            raise UnsupportedConstraint(f"unsupported regex feature {str(op).lower()}")
    return "".join(out)


def _charset(items: Any) -> str:
    chars = []
    for op, arg in items:
        if op is sre_parse.LITERAL:
            chars.append(chr(arg))
        elif op is sre_parse.RANGE:
            chars.extend(chr(code) for code in range(arg[0], arg[1] + 1))
        elif op is sre_parse.CATEGORY:
            chars.append(_category(arg))
        else:
            raise UnsupportedConstraint(f"unsupported regex feature {str(op).lower()}")
    return "".join(chars)


def _category(category: Any) -> str:
    if category not in _CATEGORIES:
        raise UnsupportedConstraint(f"unsupported regex feature {str(category).lower()}")
    return _CATEGORIES[category]
