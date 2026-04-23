import datetime

import pytest


@pytest.fixture
def base_metadata():
    return {
        "title": "Test Post",
        "date": datetime.date(2026, 1, 1),
        "permalink": "test-post",
        "tags": ["Python", "Testing"],
    }
