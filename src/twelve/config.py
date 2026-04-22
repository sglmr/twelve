import datetime
from email.utils import formatdate as _rfc822
from functools import cache
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


@cache
def get_jinja_env(input: Path, version: str = "") -> Environment:
    """Returns a jinja2 Environment for rendering templates."""
    templates_dir = input / "_layouts"
    env = Environment(loader=FileSystemLoader(str(templates_dir)))
    env.filters["markdown"] = md_to_html
    env.filters["rfc3339"] = rfc3339_format
    env.filters["rfc822"] = rfc822_format
    env.filters["displayDate"] = display_date_filter
    return env


# endregion
