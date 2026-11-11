import subprocess
import sys

SCRIPT = """
import sys
from dataclasses import dataclass
from polarfactory import build

@dataclass
class User:
    id: int

build(User)
assert "pydantic" not in sys.modules, "polarfactory imported pydantic"
"""


def test_core_never_imports_pydantic() -> None:
    subprocess.run([sys.executable, "-c", SCRIPT], check=True)
