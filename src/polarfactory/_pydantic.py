"""Pydantic v2 support. Only imported once the user has imported pydantic themselves."""

from typing import Any

import pydantic

from polarfactory._build import _FieldSpec
from polarfactory._constraints import Constraints
from polarfactory.errors import GenerationError


def is_model(tp: Any) -> bool:
    return isinstance(tp, type) and issubclass(tp, pydantic.BaseModel)


def field_specs(cls: type[pydantic.BaseModel]) -> list[_FieldSpec]:
    return [
        _FieldSpec(name, info.annotation, constraints=Constraints.from_metadata(info.metadata))
        for name, info in cls.model_fields.items()
    ]


def construct(cls: type[pydantic.BaseModel], values: dict[str, Any], path: str) -> Any:
    try:
        # by_name so fields with an alias accept the attribute name we generated under.
        return cls.model_validate(values, by_name=True)
    except pydantic.ValidationError as exc:
        raise GenerationError(
            f"values for '{path}' failed {cls.__name__} validation. "
            f"Pass the failing fields as overrides. Details:\n{exc}"
        ) from exc
