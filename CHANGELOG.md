# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-11-11

First public release.

### Added

- `build(cls, seed=..., **overrides)` creates one object filled with test data.
  Works with dataclasses, plain classes (fields read from `__init__` type hints)
  and, with the `pydantic` extra, Pydantic v2 models.
- `build_many(cls, n, seed=...)` creates `n` different objects; the same seed
  gives the same list.
- `register(type, fn)` adds a generator for a custom type, and
  `reset_registry()` restores the defaults.
- Supported types: `int`, `float`, `bool`, `str`, `bytes`, `Decimal`, `UUID`,
  `datetime`, `date`, `time`, `timedelta`, `Enum`, `Literal`, `list`, `set`,
  `dict`, `tuple`, `Optional` and `Union`, nested classes, and
  self-referencing classes (stopped at depth 3).
- Realistic `str` values for fields named `email`, `name`, `first_name`,
  `last_name`, `city`, `country`, `url`, `phone`, `username`, `title`,
  `description` and `slug`.
- Pydantic `Field` constraints: `ge`, `gt`, `le`, `lt`, `min_length`,
  `max_length` and basic `pattern` regexes.
- Error classes `PolarFactoryError` and `GenerationError` in
  `polarfactory.errors`. Both subclass `TypeError`, and every message says how to
  fix the problem.

[0.1.0]: https://github.com/PinnLabs/Polars/releases/tag/v0.1.0
