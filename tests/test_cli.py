from datetime import datetime
from pathlib import Path

import pytest

from twelve.cli import (
    create_post_data,
    get_template_content,
    print_template_choices,
    should_ignore_watch_path,
    template_choices,
)


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


def test_should_ignore_watch_path():
    # Setup dummy paths (they don't even need to exist on your disk!)
    src = Path("/my_blog/content").resolve()
    dist = Path("/my_blog/_site").resolve()

    # Case 1: A normal markdown file (Should NOT ignore)
    assert should_ignore_watch_path("/my_blog/content/post.md", src, dist) is False

    # Case 2: A file inside the output directory (Should ignore)
    assert should_ignore_watch_path("/my_blog/_site/index.html", src, dist) is True

    # Case 3: A hidden file like .DS_Store (Should ignore)
    assert should_ignore_watch_path("/my_blog/content/.DS_Store", src, dist) is True

    # Case 4: A file inside a hidden folder like .git (Should ignore)
    assert should_ignore_watch_path("/my_blog/.git/config", src, dist) is True


def test_template_choices_finds_markdown_files(tmp_path: Path):
    """It should return the stems of all .md files in the directory."""
    # 1. SETUP: Create some dummy files in the temp directory
    (tmp_path / "post.md").write_text("content")
    (tmp_path / "page.md").write_text("content")
    (tmp_path / "README.txt").write_text("should be ignored")

    # 2. EXECUTE
    results = template_choices(tmp_path)

    # 3. ASSERT
    # We sort the results because glob order can vary by OS
    assert sorted(results) == ["page", "post"]


def test_template_choices_ignores_non_markdown(tmp_path: Path):
    """It should ignore files that don't end in .md."""
    (tmp_path / "style.css").write_text("body {}")
    (tmp_path / "image.png").write_bytes(b"")

    results = template_choices(tmp_path)

    assert results == []


def test_template_choices_empty_directory(tmp_path: Path):
    """It should return an empty list if the directory is empty."""
    results = template_choices(tmp_path)
    assert results == []


def test_print_template_choices_output(tmp_path: Path, capsys):
    """Verifies the printed format of the template list."""
    # Create some dummy templates
    (tmp_path / "post.md").touch()
    (tmp_path / "page.md").touch()
    (tmp_path / "link.html").touch()

    # Call the function
    print_template_choices(tmp_path)

    # Grab the printed output
    captured = capsys.readouterr()

    # Check the contents of the output (stdout)
    assert "Available templates:" in captured.out
    assert " - post" in captured.out
    assert " - page" in captured.out
    assert " - link" not in captured.out
