import pytest

from codemigrate.config import get_settings
from codemigrate.kb.schema import load_kb


@pytest.fixture(scope="session")
def kb():
    return load_kb(get_settings().kb_path)
