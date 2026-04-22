import datetime
from pathlib import Path

import pytest

from twelve.config import Config


@pytest.fixture
def cfg(tmp_path: Path) -> Config:
    config = Config(src_dir=tmp_path / "src", dist_dir=tmp_path / "_site")
    return config


@pytest.fixture
def base_metadata():
    return {
        "title": "Test Post",
        "date": datetime.date(2026, 1, 1),
        "permalink": "test-post",
        "tags": ["Python", "Testing"],
    }
