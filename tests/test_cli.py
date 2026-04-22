from datetime import datetime
from pathlib import Path

import pytest

from twelve.cli import create_post_data, get_template_content


def test_get_template_content_finds_and_reads_file(tmp_path: Path):
    # setup the test
    template_file = tmp_path / "blog-post.md"
    template_file.write_text("Hello from the template!")
    template_file = tmp_path / "blog-post-2.md"
    template_file.write_text("I built another SSG!")

    # Call the function
    content = get_template_content(template_name="blog-post-2", templates_dir=tmp_path)

    # assert
    assert content == "I built another SSG!"


def test_get_template_content_raises_ambiguous_value_error(tmp_path: Path):
    # setup the test
    template_file = tmp_path / "blog-post.md"
    template_file.write_text("Hello from the template!")
    template_file = tmp_path / "blog-post-2.md"
    template_file.write_text("I built another SSG!")

    # assert
    with pytest.raises(ValueError):
        get_template_content(template_name="blog", templates_dir=tmp_path)


def test_get_template_content_raises_error_if_not_found(tmp_path: Path):
    # Create a directory but put nothing in it
    with pytest.raises(FileNotFoundError):
        get_template_content(template_name="missing", templates_dir=tmp_path)


def test_create_post_data():
    # Setup data
    raw_template = "# {{ title }}\nDate: {{ date }}"
    my_date = datetime(2026, 4, 21)

    # Run function
    content, dest = create_post_data(
        title="Testing is Fun",
        template_name="post",
        template=raw_template,
        date=my_date,
        input=Path("content"),
    )

    # THEN
    assert "Testing is Fun" in content
    assert "2026-04-21" in content
    assert str(dest) == "content/posts/2026/testing-is-fun.md"
