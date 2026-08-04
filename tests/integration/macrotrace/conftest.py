from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
MACROTRACE_ROOT = REPO_ROOT / "services" / "macrotrace"
if str(MACROTRACE_ROOT) not in sys.path:
    sys.path.insert(0, str(MACROTRACE_ROOT))


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def sample_request(repo_root: Path) -> dict[str, Any]:
    return json.loads((repo_root / "fixtures" / "contracts" / "sample_tool_request.json").read_text(encoding="utf-8"))
