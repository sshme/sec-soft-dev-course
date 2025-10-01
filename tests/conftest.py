# tests/conftest.py
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]  # корень репозитория
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def reset_highlights_db():
    from app.storage import storage

    storage.reset_to_default()

    yield

    storage.reset_to_default()
