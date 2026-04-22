import datetime
from pathlib import Path

import pytest

from twelve.generator import create_page_object, discover_data, should_process


# region discover_pages
def test_should_process_logic():
    base = Path("/src")

    # We can create Path objects that don't exist on disk!
    assert should_process(base / "blog/post.md", base) is True
    assert should_process(base / "pages/drafts/about.html.jinja", base) is True
    assert should_process(base / "pages/drafts/_about.html.jinja", base) is True
    assert should_process(base / "_templates/base.html", base) is False
    assert should_process(base / "docs/_drafts/secret.md", base) is False
    assert should_process(base / "docs/_drafts/base.html.jinja", base) is False


# endregion


# region discover_data
def test_discover_data_success(tmp_path):
    """Test that valid JSON, YAML, and CSV files are loaded correctly."""
    # 1. Setup: Create a mix of valid files
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Create a JSON file
    (data_dir / "site_info.json").write_text('{"name": "My SSG"}')

    # Create a YAML file with a "messy" name to test slugification
    (data_dir / "Navigation Menu.yaml").write_text("- home\n- about")

    # Create a CSV file
    (data_dir / "authors.csv").write_text("name,role\nAlice,Admin\nBob,Editor")

    # 2. Execution
    result = discover_data(data_dir)

    # 3. Assertions
    assert result["site_info"]["name"] == "My SSG"
    assert result["navigation_menu"] == ["home", "about"]  # Check slugified key
    assert len(result["authors"]) == 2
    assert result["authors"][0]["name"] == "Alice"


def test_discover_data_ignores_unsupported_files(tmp_path):
    """Ensure .txt or .png files don't end up in the data dictionary."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "notes.txt").write_text("Hello world")
    (data_dir / "config.json").write_text('{"key": "val"}')

    result = discover_data(data_dir)

    assert "config" in result
    assert "notes" not in result


def test_discover_data_handles_malformed_files(tmp_path, caplog):
    """Ensure one broken file doesn't crash the entire discovery process."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Valid file
    (data_dir / "valid.json").write_text('{"a": 1}')
    # Broken file (missing closing brace)
    (data_dir / "broken.json").write_text('{"a": 1')

    result = discover_data(data_dir)

    # Valid file should still be there
    assert result["valid"]["a"] == 1
    # Broken file should be skipped
    assert "broken" not in result
    # Check that we logged an error (using pytest's caplog fixture)
    assert "Failed to parse data file" in caplog.text


def test_discover_data_nonexistent_directory():
    """Ensure it returns an empty dict if the directory doesn't exist."""
    path = Path("/non/existent/path")
    result = discover_data(path)
    assert result == {}


# endregion

# region create_page
## --- HAPPY PATH TESTS ---


def test_create_page_object_basic(base_metadata):
    """Test that a standard metadata dict produces a correct Page object."""
    source = Path("content/posts/test.md")
    content = "Hello World"

    page = create_page_object(content, base_metadata, source)

    assert page["title"] == "Test Post"
    assert page["permalink"] == "/test-post"  # Verify slash addition
    assert page["url"] == "/test-post"
    assert page["is_page"] is False
    assert page["raw_content"] == content


## --- PERMALINK EDGE CASES ---


@pytest.mark.parametrize(
    "input_link, expected",
    [
        ("about", "/about"),
        ("/about", "/about"),
        ("", "/"),
        ("blog/post-1", "/blog/post-1"),
    ],
)
def test_permalink_normalization(base_metadata, input_link, expected):
    """Ensures permalinks always start with a slash regardless of input."""
    base_metadata["permalink"] = input_link
    page = create_page_object("", base_metadata, Path("x.md"))
    assert page["permalink"] == expected


## --- PAGE VS POST LOGIC ---


@pytest.mark.parametrize(
    "path_str, expected_is_page",
    [
        ("src/pages/about.md", True),
        ("content/posts/my-post.md", False),
        ("pages/index.html", True),
        ("blog/pages/about.html", True),
        (
            "blog/2026/pages-are-cool.md",
            False,
        ),  # 'pages' is in the filename, not a directory
    ],
)
def test_is_page_detection(base_metadata, path_str, expected_is_page):
    """Verifies the function correctly identifies static pages vs posts based on path."""
    page = create_page_object("", base_metadata, Path(path_str))
    assert page["is_page"] is expected_is_page


## --- DATE HANDLING ---


def test_date_defaults_to_today(base_metadata):
    """If no date is provided, it should default to today's date."""
    del base_metadata["date"]

    # We use a mock to freeze 'today' so the test doesn't change tomorrow
    today = datetime.date.today()
    page = create_page_object("", base_metadata, Path("x.md"))

    assert page["date"] == today


## --- DYNAMIC METADATA (THE "EXTRA KEYS" RULE) ---


def test_extra_metadata_keys_are_preserved(base_metadata):
    """Test that non-standard frontmatter keys are added to the Page object."""
    base_metadata["author"] = "Alice"
    base_metadata["hero_image"] = "/img/top.jpg"
    base_metadata["custom_flag"] = True

    page = create_page_object("", base_metadata, Path("x.md"))

    assert page["author"] == "Alice"
    assert page["hero_image"] == "/img/top.jpg"
    assert page.get("custom_flag") is True


## --- HIDDEN CONTENT ---


@pytest.mark.parametrize(
    "hidden_val, expected",
    [
        (True, True),
        (False, False),
        (None, False),  # Should default to False if weird data passed
    ],
)
def test_hidden_status(base_metadata, hidden_val, expected):
    if hidden_val is None:
        if "hidden" in base_metadata:
            del base_metadata["hidden"]
    else:
        base_metadata["hidden"] = hidden_val

    page = create_page_object("", base_metadata, Path("x.md"))
    assert page["hidden"] is expected


# endregion
