from importlib.metadata import version

import polarfactory


def test_version_matches_package_metadata() -> None:
    # __version__ is written by hand, so catch it drifting from pyproject.toml.
    assert polarfactory.__version__ == version("polarfactory")
