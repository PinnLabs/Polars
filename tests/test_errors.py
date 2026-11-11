from dataclasses import InitVar, dataclass, field

import pytest

from polarfactory import build
from polarfactory.errors import GenerationError, PolarFactoryError


@dataclass
class WithInitVar:
    id: int
    scale: InitVar[int]
    received: int = field(init=False)

    def __post_init__(self, scale: int) -> None:
        self.received = scale


@dataclass
class Order:
    total: "Money"  # type: ignore[name-defined]  # noqa: F821


@dataclass
class HoldsOrder:
    order: Order


class PlainOrder:
    def __init__(self, total: "Money") -> None:  # type: ignore[name-defined]  # noqa: F821
        self.total = total


def unresolved(cls_name: str) -> str:
    return (
        f"cannot resolve type hints of {cls_name}: name 'Money' is not defined. "
        f"Define or import it in module '{__name__}'"
    )


def test_hierarchy_keeps_type_error_compatibility() -> None:
    assert issubclass(GenerationError, PolarFactoryError)
    assert issubclass(PolarFactoryError, TypeError)


def test_init_var_is_generated_and_passed_to_post_init() -> None:
    built = build(WithInitVar, seed=1)
    assert type(built.received) is int
    assert built == build(WithInitVar, seed=1)


def test_init_var_can_be_overridden() -> None:
    assert build(WithInitVar, seed=1, scale=2).received == 2


@pytest.mark.parametrize(
    ("cls", "owner"), [(Order, "Order"), (HoldsOrder, "Order"), (PlainOrder, "PlainOrder")]
)
def test_unresolvable_annotation_raises_generation_error(cls: type, owner: str) -> None:
    with pytest.raises(GenerationError) as exc:
        build(cls)
    assert str(exc.value) == unresolved(owner)
