from pathlib import Path

import pytest

from src.utils import md_to_html, normalize_tags, safe_write


# region safe_write
def test_safe_write_creates_file(tmp_path: Path):
    # Setup: Define a file path and content
    test_file = tmp_path / "test-create.txt"
    content = "Hello safe write!"

    # Act: Call safe_write
    safe_write(test_file, content)

    # Assert: check if it worked
    assert test_file.exists()
    assert test_file.read_text() == content


def test_safe_write_fails_if_exists(tmp_path):
    # Setup: Create a file
    test_file = tmp_path / "already_here.txt"
    test_file.write_text("Original Content")

    # Act & Assert: Writing to an existing file should fail
    with pytest.raises(FileExistsError):
        safe_write(test_file, "New Content")


# endregion


# region normalize_tags
@pytest.mark.parametrize(
    "input_value, expected",
    [
        ("Python", ["python"]),
        ("  AI  ", ["ai"]),
        (["Python", "python", "AI"], ["python", "ai"]),
        (["tag1", "  tag1  ", "TAG2"], ["tag1", "tag2"]),
        (None, []),
        ("", []),
        ([], []),
        ([" ", ""], []),
        (123, ["123"]),
        ([1, 2.5], ["1", "2.5"]),
        (["python", "", None, "  java  "], ["python", "java"]),
    ],
)
def test_normalize_tags_behavior(input_value, expected):
    """Verifies that various inputs are correctly flattened and cleaned."""
    assert normalize_tags(input_value) == expected


def test_normalize_tags_preserves_order():
    """Ensures that the first appearance of a tag determines its position."""
    input_data = ["zebra", "apple", "ZEBRA", "apple"]
    expected = ["zebra", "apple"]
    assert normalize_tags(input_data) == expected


# endregion


# region MD tests
@pytest.mark.parametrize(
    "md_input, expected_snippet",
    [
        # 1. sane_lists & tasklist
        ("- [x] Task Done", 'class="task-list-item"'),
        ("- [ ] Task Pending", 'type="checkbox"'),
        # 2. tilde (Strikethrough)
        ("~~strike~~", "<del>strike</del>"),
        # 3. mark (Highlight)
        ("==highlight==", "<mark>highlight</mark>"),
        # 4. magiclink
        ("Check https://google.com", 'href="https://google.com"'),
        # 5. saneheaders (Should NOT be a header if no space)
        ("#NoSpace", "<p>#NoSpace</p>"),
        ("# Space", "<h1>Space</h1>"),
        # 6. admonitions
        ("> [!INFO]\n> this is a note", 'class="admonition info"'),
    ],
)
def test_markdown_extensions(md_input, expected_snippet):
    """Verify that specific extensions are rendering the expected HTML tags."""
    html = md_to_html(md_input)
    assert expected_snippet in html


def test_superfences_mermaid():
    """Verify that the custom mermaid fence is applied."""
    content = "```mermaid\ngraph TD; A-->B;\n```"
    html = md_to_html(content)
    # Check for the class and div format you defined in your config
    assert 'class="mermaid"' in html
    assert "graph TD;" in html


def test_footnotes():
    """Verify footnotes render and link correctly."""

    content = "Text with a footnote[^1]\n\n[^1]: The footnote content"
    html = md_to_html(content)
    assert 'class="footnote-ref"' in html
    assert 'class="footnote-backref"' in html
    assert "The footnote content" in html


def test_markdown_reset_logic():
    """
    Verify that md.reset() prevents footnote leakage.
    If reset() isn't called, the second conversion might contain
    references from the first.
    """
    _ = md_to_html("[^1]: Footnote A")
    second_run = md_to_html("Just some text")

    # The second run should NOT contain footnote HTML if reset() worked
    assert 'class="footnote"' not in second_run


# endregion
