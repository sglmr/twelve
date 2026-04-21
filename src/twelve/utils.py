from collections.abc import Iterable
from pathlib import Path
from typing import Any

import markdown
from pymdownx.superfences import fence_div_format


def safe_write(file_path: Path | str, content: str):
    """Safely writes a content to a file at the given file_path.
    Raises a validation error if the file already exists."""

    path = Path(file_path)

    # Create the parent directories
    path.parent.mkdir(parents=True, exist_ok=True)

    # use 'x' mode for atomic writes
    with path.open(mode="x", encoding="utf-8") as f:
        f.write(content)


def normalize_tags(value: Any) -> list[str]:
    """
    Standardizes tags into a list. Handles lists, single values, and emptry values.
    """
    # 1. Handle missing or null values
    if not value:
        return []

    # Treat strings and non-iterables as a single-item collection
    if isinstance(value, (str, bytes)) or not isinstance(value, Iterable):
        items = [value]
    else:
        items = value

    # Clean, stringify, and lowercase items
    cleaned = [
        str(t).strip().lower() for t in items if t is not None and str(t).strip()
    ]

    # De-duplicate while preserving order
    return list(dict.fromkeys(cleaned))


# One seriously over-engineered markdown convertor
md = markdown.Markdown(
    extensions=[
        "sane_lists",  # Better list handling, especially with nested lists
        # part of pymdown 'Extra'
        "pymdownx.betterem",  # better _emphasis_
        "pymdownx.superfences",
        "footnotes",  # footnotes with [^1]:
        "tables",  # markdown tables
        "md_in_html",  # convert markdown in html tags
        # Other things
        "pymdownx.highlight",  # code block highlighting with pygments
        "pymdownx.tasklist",  # List with '- [ ]' or '- [x]'
        "pymdownx.saneheaders",  # require spaces for headers
        "pymdownx.magiclink",  # auto-link http:// & https://
        "pymdownx.tilde",  # ~~strikethrough~~
        "pymdownx.mark",  # ==mark highlight==
        "pymdownx.blocks.admonition",
        "pymdownx.quotes",
    ],
    extension_configs={
        "pymdownx.blocks.admonition": {
            "types": ["note", "info", "tip", "warning"],
        },
        "pymdownx.highlight": {
            "noclasses": True,
            "use_pygments": True,
            "pygments_style": "default",
            "pygments_lang_class": False,  # 1password extension js breaks highlighting if this is True
        },
        "pymdownx.tilde": {"subscript": False},
        "pymdownx.superfences": {
            "disable_indented_code_blocks": True,  # Only use ``` fenced code blocks, not indented ones
            "custom_fences": [
                {
                    "name": "mermaid",
                    "class": "mermaid",
                    "format": fence_div_format,
                }
            ],
        },
        "pymdownx.quotes": {
            "callouts": True,
        },
    },
    output_format="html",
)


def md_to_html(text: str) -> str:
    """Converts markdown to html"""
    html = md.convert(text)
    md.reset()
    return html
