from pathlib import Path

import pytest
from PIL import Image
from PIL.ExifTags import TAGS

CONTENT_DIR = Path("content")
ASSETS_DIR = CONTENT_DIR / "_assets"
MAX_WIDTH = 1600

# Supported image extensions
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif"}

# Files we process as text/data or copy as-is (non-images)
NON_IMAGE_EXTENSIONS = {
    # Content & Data
    ".md",
    ".html",
    ".txt",
    ".json",
    ".xml",
    # Assets
    ".css",
    ".js",
    # Downloads
    ".pdf",
    ".zip",
    ".xmi",
    ".clar",
    # Configs
    ".toml",
    ".yaml",
    ".yml",
    # Templates
    ".jinja",
}

# Files we explicitly want to ignore (OS junk, etc.)
IGNORED_EXTENSIONS = {".DS_Store", ".thumbs.db", ".gitignore"}


def iter_content():
    """Helper to fetch every file path in the content directory."""

    # We only return files, ignoring directories themselves
    for p in CONTENT_DIR.rglob("*"):
        if p.is_file() and p.name != ".DS_Store":
            yield p


def iter_images():
    """Helper to find all images in the content directory."""
    for p in iter_content():
        if p.suffix in IMAGE_EXTENSIONS:
            yield p


def iter_asset_paths():
    """Returns filenames (or relative paths) in the assets folder."""
    for f in ASSETS_DIR.rglob("*"):
        if f.is_file() and f.name != ".DS_Store":
            yield f"assets/{f.relative_to(ASSETS_DIR)}"


@pytest.mark.parametrize(
    "asset_path", [p for p in iter_asset_paths()], ids=lambda p: f"{p}"
)
def test_no_orphaned_assets(asset_path: str):
    """
    Fails if an asset file isn't referenced in another content file.
    """
    found_count = 0
    for file_path in iter_content():
        try:
            if asset_path in file_path.read_text():
                found_count = 1
                break
        except UnicodeDecodeError:
            continue
    assert found_count > 0, f"Orphaned asset '{asset_path}'."


@pytest.mark.parametrize(
    "file_path", [p for p in iter_content()], ids=lambda p: f"{p.parent.name}/{p.name}"
)
def test_all_file_extensions_are_considered(file_path: Path):
    """
    Fails if a file has an extension not defined in:
    - IMAGE_EXTENSIONS
    - NON_IMAGE_EXTENSIONS
    - IGNORED_EXTENSIONS
    """
    ext = file_path.suffix or file_path.name

    # Create a master set of everything we've accounted for
    all_allowed = IMAGE_EXTENSIONS | NON_IMAGE_EXTENSIONS | IGNORED_EXTENSIONS

    # If the file has no extension, Path.suffix returns an empty string ""
    # You might want to handle extensionless files specifically
    display_ext = ext if ext else "[No Extension]"

    assert ext in all_allowed, (
        f"Unhandled file type found: '{display_ext}'\n"
        f"File: {file_path.relative_to(CONTENT_DIR)}\n"
        f"Please add this extension to IMAGE_EXTENSIONS or NON_IMAGE_EXTENSIONS."
    )


@pytest.mark.parametrize(
    "image_path", [p for p in iter_images()], ids=lambda p: f"{p.parent.name}/{p.name}"
)
def test_image_width_limit(image_path):
    """Ensure that no image exceeds the maximum allowed width."""
    with Image.open(image_path) as img:
        width, height = img.size

    assert width <= MAX_WIDTH, (
        f"Image '{image_path.relative_to(CONTENT_DIR)}' is too wide! "
        f"Current: {width}px, Max: {MAX_WIDTH}px."
    )


@pytest.mark.parametrize(
    "image_path", [p for p in iter_images()], ids=lambda p: f"{p.parent.name}/{p.name}"
)
def test_no_identifying_metadata(image_path):
    """Ensure images do not contain GPS or other identifying EXIF data."""
    with Image.open(image_path) as img:
        # getexif() handles modern formats like WebP and JPG
        exif_data = img.getexif()

        # Check for GPS Info specifically (Tag 34853)
        # We also check the 'info' dict which can hold XMP or other metadata
        has_gps = 34853 in exif_data or "gpsinfo" in img.info

        assert not has_gps, (
            f"PRIVACY LEAK: Image '{image_path.name}' contains GPS coordinates!"
        )

        # Check for general identifying tags (Camera, Software, DateTime)
        # Some metadata is harmless (like orientation), but if the dict is
        # populated with more than a few items, it's a sign it hasn't been stripped.
        sensitive_tags = []
        for tag_id, value in exif_data.items():
            tag_name = TAGS.get(tag_id, tag_id)
            if tag_name in [
                "Make",
                "Model",
                "Software",
                "DateTime",
                "Artist",
                "Copyright",
            ]:
                sensitive_tags.append(tag_name)

        assert not sensitive_tags, (
            f"Image '{image_path.name}' contains sensitive metadata: {', '.join(sensitive_tags)}. "
            "Please strip EXIF data before committing."
        )

        # 2. Check GIF-specific comments
        # Pillow stores GIF comments in img.info
        if image_path.suffix.lower() == ".gif":
            comment = img.info.get("comment", b"").decode("utf-8", "ignore")
            # Check for common software signatures or timestamps
            sensitive_keywords = ["Photoshop", "GIMP", "Created with", "2026:"]
            for word in sensitive_keywords:
                assert word not in comment, (
                    f"GIF comment in {image_path.name} contains {word}"
                )
