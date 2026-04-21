import datetime
from dataclasses import dataclass, field
from email.utils import formatdate as _rfc822
from functools import cached_property
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from twelve.utils import md_to_html


# region Jinja
def display_date_filter(value, format="%B %d, %Y"):
    """Format a date object or string into a pretty format."""
    if not value:
        return ""

    # If it's a string, try to convert it to a datetime object first
    if isinstance(value, str):
        try:
            value = datetime.datetime.fromisoformat(value)
        except ValueError:
            return value

    return value.strftime(format)


def rfc3339_format(value):
    """
    Converts a datetime object into an RFC-3339 string.
    Example: 2026-04-12T21:55:18+00:00
    """
    # Check if it's a date but NOT a datetime
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        value = datetime.datetime.combine(value, datetime.time.min)

    # Atom requires a timezone offset. If missing, assume UTC.
    if value.tzinfo is None:
        value = value.replace(tzinfo=datetime.timezone.utc)

    return value.isoformat()


def rfc822_format(value):
    """
    Converts a datetime object into an RFC-822 string.
    Example: 2026-04-12T21:55:18+00:00
    """
    # If it's a date (no time), convert to datetime
    if not isinstance(value, datetime.datetime):
        value = datetime.datetime.combine(value, datetime.time.min)

    # Atom requires a timezone offset. If missing, assume UTC.
    if value.tzinfo is None:
        value = value.replace(tzinfo=datetime.timezone.utc)

    return _rfc822(value.timestamp(), localtime=True)


# Set up jinja templates & filters
def jinja_loader(layout_dir: Path) -> Environment:
    env = Environment(loader=FileSystemLoader(str(layout_dir)))
    env.filters["markdown"] = md_to_html
    env.filters["rfc3339"] = rfc3339_format
    env.filters["rfc822"] = rfc822_format
    env.filters["displayDate"] = display_date_filter
    return env


# endregion


@dataclass(frozen=True)
class Config:
    src_dir: Path
    dist_dir: Path
    verbose: bool = False
    build_date: datetime.datetime = field(default_factory=datetime.datetime.now)

    @property
    def layout_dir(self) -> Path:
        return self.src_dir / "_layouts"

    @property
    def data_dir(self) -> Path:
        return self.src_dir / "_data"

    @property
    def template_dir(self) -> Path:
        return self.src_dir / "_templates"

    @property
    def assets_dir(self) -> Path:
        return self.src_dir / "_assets"

    @property
    def pages_dir(self) -> Path:
        return self.src_dir / "pages"

    @cached_property
    def env(self) -> Environment:
        # Lazy load Jinja only when accessed
        return jinja_loader(self.layout_dir)
