import datetime
from pathlib import Path

import frontmatter
import pytest

from twelve.generator import (
    create_page_object,
    discover_data_files,
    is_valid_content_file,
    load_page,
)


# region load_page
@pytest.mark.parametrize(
    "sub_path, content, metadata",
    [
        # Scenario 1: A standard page
        (
            "pages/about.md",
            "Hello world",
            {"title": "About Me", "permalink": "about"},
        ),
        # Scenario 2: A blog post (not in /pages/)
        (
            "blog/my-post.md",
            "Post content",
            {"title": "My Post", "date": datetime.date(2023, 1, 1)},
        ),
        # Scenario 3: Recipe with dynamic fields
        (
            "recipes/cookies.md",
            "Bake at 350",
            {
                "title": "Cookies",
                "ingredients": ["flour", "sugar"],
                "instructions": ["mix", "bake"],
            },
        ),
        # Scenario 4: Jinja template
        (
            "pages/timer.html",
            "<p>A Jinja post.<p>",
            {
                "title": "Jinja Post",
                "tags": ["python", "jinja"],
            },
        ),
    ],
    ids=lambda val: val,
)
def test_load_page_variations(sub_path, content, metadata, tmp_path):
    # Setup: Create the file with frontmatter
    file_path = tmp_path / sub_path
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Create the frontmatter file content
    post = frontmatter.Post(content, **metadata)
    file_path.write_text(frontmatter.dumps(post))

    # 2. Execution
    page = load_page(file_path)

    # 3. Assertions
    assert page["title"] == metadata["title"]
    assert page["raw_content"] == content
    assert page["source_path"] == file_path

    # Check permalink formatting (should always start with /)
    if "permalink" in metadata:
        assert page["permalink"].startswith("/")
        assert metadata["permalink"] in page["permalink"]

    # Verify dynamic fields (like ingredients in the recipe scenario)
    for key, value in metadata.items():
        if key == "permalink":
            continue  # already tested permalink
        assert page[key] == value


# endregon


# region is_valid_content
@pytest.mark.parametrize(
    "sub_path, expected",
    [
        ("blog/post.md", True),
        ("pages/drafts/about.html.jinja", True),
        ("pages/drafts/about.html", False),
        ("pages/drafts/_about.html.jinja", True),
        ("_templates/base.html", False),
        ("docs/_drafts/secret.md", False),
        (".site/secret.md", False),
        ("docs/_drafts/base.html.jinja", False),
        (".DS_Store", False),
        ("assets/post.md", False),
        ("assets/photo.jpg", False),
        ("blog/assets/post.md", True),
    ],
    ids=lambda p: p,  # Uses the sub_path string as the ID
)
def test_is_valid_content_file_logic(sub_path, expected, tmp_path):
    test_file = tmp_path / sub_path
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.touch()

    assert is_valid_content_file(path=test_file, input=tmp_path) is expected


def test_is_valid_content_has_to_be_a_file(tmp_path):
    """Returns False if the file doesn't exist"""
    test_file = tmp_path / "i-dont-exist-ever-ever-ever.txt"

    assert is_valid_content_file(path=test_file, input=tmp_path) is False


# endregion


# region discover_data_files
def test_discover_data_files_success(tmp_path):
    """Test that valid JSON, YAML, and CSV files are loaded correctly."""
    # 1. Setup: Create a mix of valid files
    data_dir = tmp_path / "_data"
    data_dir.mkdir()

    # Create a JSON file
    (data_dir / "site_info.json").write_text('{"name": "My SSG"}')

    # Create a YAML file with a "messy" name to test slugification
    (data_dir / "Navigation Menu.yaml").write_text("- home\n- about")

    # Create a CSV file
    (data_dir / "authors.csv").write_text("name,role\nAlice,Admin\nBob,Editor")

    # 2. Execution
    result = discover_data_files(tmp_path)

    # 3. Assertions
    assert result["site_info"]["name"] == "My SSG"
    assert result["navigation_menu"] == ["home", "about"]  # Check slugified key
    assert len(result["authors"]) == 2
    assert result["authors"][0]["name"] == "Alice"


def test_discover_data_files_ignores_unsupported_files(tmp_path):
    """Ensure .txt or .png files don't end up in the data dictionary."""
    data_dir = tmp_path / "_data"
    data_dir.mkdir()
    (data_dir / "notes.txt").write_text("Hello world")
    (data_dir / "config.json").write_text('{"key": "val"}')

    result = discover_data_files(tmp_path)

    assert "config" in result
    assert "notes" not in result


def test_discover_data_files_handles_malformed_files(tmp_path, caplog):
    """Ensure one broken file doesn't crash the entire discovery process."""
    data_dir = tmp_path / "_data"
    data_dir.mkdir()

    # Valid file
    (data_dir / "valid.json").write_text('{"a": 1}')
    # Broken file (missing closing brace)
    (data_dir / "broken.json").write_text('{"a": 1')

    result = discover_data_files(tmp_path)

    # Valid file should still be there
    assert result["valid"]["a"] == 1
    # Broken file should be skipped
    assert "broken" not in result
    # Check that we logged an error (using pytest's caplog fixture)
    assert "Failed to parse data file" in caplog.text


def test_discover_data_files_nonexistent_directory():
    """Ensure it returns an empty dict if the directory doesn't exist."""
    path = Path("/non/existent/path")
    result = discover_data_files(path)
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


# endregion
