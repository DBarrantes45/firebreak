import os

import pytest

# main.py reads the chaos switch when it is imported, so it has to be set
# before any test imports it.
os.environ["FIREBREAK_CHAOS_ENABLED"] = "true"

import main
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    # Not used as a context manager on purpose: that skips the lifespan,
    # so no database is needed for these tests.
    return TestClient(main.app)


@pytest.fixture(autouse=True)
def reset_chaos():
    yield
    for key in main.chaos_settings:
        main.chaos_settings[key] = 0
