import pytest
import requests

BASE_URL = "http://localhost:5000"
API_PREFIX = "/api/v1"


def pytest_collection_modifyitems(config, items):
    """If API health endpoint is unreachable, mark all collected tests as skipped."""
    try:
        requests.get(f"{BASE_URL}{API_PREFIX}/health", timeout=2)
    except Exception:
        skip = pytest.mark.skip(reason="API server not running")
        for item in items:
            item.add_marker(skip)
