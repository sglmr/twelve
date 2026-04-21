import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from src.config import Config, display_date_filter, jinja_loader, rfc822_format, rfc3339_format
from src.utils import md_to_html


# region diplay_date_filter
def test_display_date_filter_valid_datetime():
    dt = datetime.datetime(2026, 4, 20)
    assert display_date_filter(dt) == "April 20, 2026"


def test_display_date_filter_iso_string():
    assert display_date_filter("2026-04-20") == "April 20, 2026"


def test_display_date_filter_custom_format():
    dt = datetime.datetime(2026, 4, 20)
    assert display_date_filter(dt, format="%Y/%m/%d") == "2026/04/20"


def test_display_date_filter_none():
    assert display_date_filter(None) == ""


def test_display_date_filter_invalid_string():
    # Should return the original string if parsing fails
    assert display_date_filter("not-a-date") == "not-a-date"


# endregion


# region rfc339_format
def test_rfc3339_format_naive_datetime():
    dt = datetime.datetime(2026, 4, 20, 14, 0)
    # It should assume UTC if no timezone is provided
    result = rfc3339_format(dt)
    assert "2026-04-20T14:00:00+00:00" in result


def test_rfc3339_format_date_object():
    d = datetime.date(2026, 4, 20)
    result = rfc3339_format(d)
    assert "2026-04-20T00:00:00+00:00" in result


# endregion


# region rfc822_format
def test_rfc822_format():
    dt = datetime.datetime(2026, 4, 20, 12, 0)
    result = rfc822_format(dt)
    # RFC 822 looks like: Mon, 20 Apr 2026 12:00:00 GMT (or offset)
    assert "Apr" in result
    assert "2026" in result


# endregion


# region Config
def test_config_paths(cfg: Config):
    assert isinstance(cfg.src_dir, Path)
    assert cfg.dist_dir.name == "_site"
    assert cfg.layout_dir.name == "_layouts"
    assert cfg.data_dir.name == "_data"
    assert cfg.template_dir.name == "_templates"
    assert cfg.assets_dir.name == "_assets"
    assert cfg.pages_dir.name == "pages"


# endregion Config


# region jinja
def test_jinja_loader_configuration(tmp_path):
    """
    Verifies that the Jinja environment is correctly configured with
    the right loader path and all custom filters.
    """
    # 1. Setup: Use tmp_path to simulate a layouts directory
    layout_dir = tmp_path / "templates"
    layout_dir.mkdir()

    # 2. Act: Run the loader
    env = jinja_loader(layout_dir)

    # 3. Assert: Verify the Environment and Loader
    assert isinstance(env, Environment)
    assert isinstance(env.loader, FileSystemLoader)

    # Jinja converts paths to strings internally, so check for the string version
    assert str(layout_dir) in env.loader.searchpath

    # 4. Assert: Verify Filter Registration
    # We check that the function in the dict IS the function we imported
    assert env.filters["markdown"] is md_to_html
    assert env.filters["rfc3339"] is rfc3339_format
    assert env.filters["rfc822"] is rfc822_format
    assert env.filters["displayDate"] is display_date_filter


def test_jinja_markdown_filter_integration(tmp_path):
    """
    An integration test to ensure the 'markdown' filter actually
    works within a rendered template.
    """
    layout_dir = tmp_path / "templates"
    layout_dir.mkdir()

    # Create a dummy template file
    template_file = layout_dir / "test.html"
    template_file.write_text("{{ content | markdown }}")

    env = jinja_loader(layout_dir)
    template = env.get_template("test.html")

    # Render and check output (assuming md_to_html turns # into <h1>)
    result = template.render(content="# Hello")
    assert "<h1>Hello</h1>" in result
