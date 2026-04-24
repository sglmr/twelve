import argparse
import os
import shutil
from datetime import datetime
from pathlib import Path

import pyvips
from rich import print
from slugify import slugify

from twelve.cli.utils import CLI_FORMATTER, print_title

MAX_DIM = 2000
QUALITY = 75
IMAGE_FORMAT_CHOICES = ("webp", "avif", "jpg")
DEFAULT_FORMAT = "webp"

project_dir = os.getenv("TWELVE_INPUT") or ""


def resolve_unique_target_path(
    source_path: Path, dest_dir: Path, target_ext: str | None = None
) -> Path:
    """Calculates the final slugified path and handles filename collisions.

    Final path: "/{dest_dir}/{year}/{slugified-file-name}.{target_ext}"

    If a file already exists, the script will add a counter to it.
    """
    # Use the source extension if one wasn't provided
    if not target_ext:
        target_ext = source_path.suffix.lower()

    # Slugify the file name
    file_name: str = slugify(source_path.stem)

    target_path = dest_dir / f"{file_name}.{target_ext}"
    # Collision avoidance: photo.webp -> photo-1.webp
    counter: int = 1
    while target_path.exists():
        target_path = dest_dir / f"{file_name}-{counter}.{target_ext}"
        counter += 1

    return target_path


def process_and_save_image(
    source_path: Path, target_path: Path, max_dim: int, quality: int
) -> None:
    """Uses pyvips to resize, rotate, and compress the image."""

    max_dim = int(max_dim)
    quality = str(quality)

    # Image.thumbnail() handles auto-rotate and efficient shrink-on-load
    image = pyvips.Image.thumbnail(str(source_path), max_dim, size="down")

    # Force sRGB color space for web consistency
    if image.interpretation != "srgb":
        image = image.colourspace("srgb")

    # Save with stripped metadata and specified quality
    image.write_to_file(str(target_path), Q=quality, strip=True)


def copy_raw_file(source_path: Path, target_path: Path) -> None:
    """Performs a standard file copy for non-image assets or fallbacks."""
    shutil.copy2(source_path, target_path)


def print_markdown_snippet(rel_path: Path) -> None:
    """Prints a helper snippet for copy-pasting into blog posts."""
    # Logic to guess a web-root path relative to your assets folder
    # Adjust '/assets/' to match your SSG's actual public URL structure

    print_title("Markdown Snippet")

    print(f"!\[{rel_path.stem}]({rel_path})")


def handle_stash(args: argparse.Namespace) -> None:
    """Coordinator function to manage the stashing workflow."""

    print_title("Stashing File")

    source: Path = Path(args.source).resolve()
    if not source.exists():
        print(f"❌ Error: Source file '{source}' not found.")
        return

    # Resolve destination directory
    project_path = Path(args.project_dir).absolute()
    dest_path = project_path / "assets" / "media" / str(datetime.now().year)
    dest_path.mkdir(parents=True, exist_ok=True)

    # Determine final destination name
    target_path: Path = resolve_unique_target_path(
        source_path=source, dest_dir=dest_path, target_ext=args.format
    )

    try:
        print(f"🖼️  Optimizing image: {target_path.name}")
        target_path = resolve_unique_target_path(
            source_path=source, dest_dir=dest_path, target_ext=args.format
        )
        process_and_save_image(
            source_path=source,
            target_path=target_path,
            max_dim=args.size,
            quality=args.quality,
        )
        print(f"✅ Image stashed successfully: '{target_path}'")
    except Exception as e:
        print(f"❌ [red]Failed to stash as an image[/red] {source.name}: {e}")
        print(f"📦 Stashing raw file: {target_path.name}")
        target_path = resolve_unique_target_path(
            source_path=source, dest_dir=dest_path, target_ext=args.format
        )
        copy_raw_file(source, target_path)
        print(f"✅ Raw file stashed successfully: '{target_path}'")

    # Print the final markdown snippet
    print_markdown_snippet(rel_path=target_path.relative_to(project_path))


def setup_stash_subparser(subparser: argparse._SubParsersAction) -> None:
    """Configures the 'stash' command and attaches it to the main subparsers."""
    stash_p = subparser.add_parser(
        "stash",
        help="Stash assets. Images can be optimized on import.",
        formatter_class=CLI_FORMATTER,
    )
    stash_p.add_argument("source", help="path to the raw file")
    stash_p.add_argument(
        "--project-dir",
        dest="project_dir",
        help=f"Override project directory for file destination (default: '{project_dir}')",
        default=project_dir,
    )
    stash_p.add_argument(
        "-s",
        "--size",
        type=int,
        dest="size",
        default=MAX_DIM,
        help=f"max longest edge in pixels (default: {MAX_DIM}px)",
    )
    stash_p.add_argument(
        "-f",
        "--format",
        default="webp",
        dest="format",
        choices=IMAGE_FORMAT_CHOICES,
        help=f"Output format (default: {DEFAULT_FORMAT})",
    )
    stash_p.add_argument(
        "-q",
        "--quality",
        type=int,
        dest="quality",
        default=QUALITY,
        help=f"quality (default: {QUALITY})",
    )

    # Pro Tip: Set a 'func' default so main() knows who to call
    stash_p.set_defaults(func=handle_stash, parser=stash_p)
