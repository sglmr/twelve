import csv
import datetime
import json
import logging
import shutil
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Generator, NotRequired, TypedDict
from zoneinfo import ZoneInfo

import frontmatter
import yaml
from rich import print
from slugify import slugify

from twelve.config import Config
from twelve.utils import md_to_html, normalize_tags, safe_write

logger = logging.getLogger(__name__)

PARSEABLE_EXTENSIONS = (".md", ".jinja")

DATA_LOADERS = {
    ".json": json.load,
    ".yaml": yaml.safe_load,
    ".yml": yaml.safe_load,
    ".csv": lambda f: list(csv.DictReader(f)),
}


class Page(TypedDict, total=False):
    # Metadata from frontmatter
    title: str
    date: datetime.date
    permalink: str
    hidden: bool
    tags: list[str]
    description: NotRequired[str | None]
    layout: NotRequired[str | None]
    is_page: bool

    # Input File details
    source_path: Path
    url: str
    raw_content: str
    content: str

    # Book specific Fields
    book_cover: NotRequired[str]
    book_authors: NotRequired[str]

    # Link specific fields
    link_url: NotRequired[str]
    source_url: NotRequired[str]

    # Recipe specific fields
    source: NotRequired[str]
    ingredients: NotRequired[list[str]]
    instructions: NotRequired[list[str]]
    notes: NotRequired[list[str]]


class Collections(TypedDict, total=False):
    posts: list[Page]
    pages: list[Page]
    hidden_posts: list[Page]
    hidden_pages: list[Page]
    tags: dict[str, list[Page]]


def create_page_object(content: str, metadata: dict, source_path: Path) -> Page:
    """Creates a Page object from the content of a file."""
    permalink = str(metadata.get("permalink", ""))
    permalink = permalink if permalink.startswith("/") else f"/{permalink}"
    page: Page = {
        "title": metadata["title"],
        "date": metadata.get("date", datetime.date.today()),
        "permalink": permalink,
        "hidden": metadata.get("hidden", False),
        "tags": normalize_tags(metadata.get("tags")),
        "layout": metadata.get("layout"),
        "is_page": "pages" in source_path.parts,
        "source_path": source_path,
        "url": permalink,
        "raw_content": content,
        "content": "",
    }

    # Add any extra frontmatter keys dynamically
    for k, v in metadata.items():
        if k not in page:
            page[k] = v

    return page


def load_page(file_path: Path) -> Page:
    """Thin wrapper that handles File I/O to create a page object."""
    post = frontmatter.load(str(file_path.resolve()))
    return create_page_object(post.content, post.metadata, file_path)


# endregion


# region readers
def should_process(path: Path, src_dir: Path) -> bool:
    """Pure logic: Decides if the file at a path should be included.
    1. The file extension is a PARSEABLE_EXTENSION
    2. The parent folder doesn't start with an underscore (i.e. not "_data")
    """
    if path.suffix not in PARSEABLE_EXTENSIONS:
        return False

    # Check if any parent (relative to src) starts with '_'
    relative_parts = path.relative_to(src_dir).parts[:-1]
    return not any(p.startswith("_") for p in relative_parts)


def discover_pages(src_dir: Path) -> Generator[Path, None, None]:
    """
    Crawls src_dir, excluding any files that shouldn't or can't
    be processed.
    """
    for file in src_dir.rglob("*"):
        if file.is_file() and should_process(path=file, src_dir=src_dir):
            yield file
        else:
            logger.debug(f"Page discovery skipping {file}")


def discover_data(data_dir: Path) -> dict[str, Any]:
    """Discover and parse the contents of data files into dictionaries."""
    global_data: dict[str, Any] = {}
    if not data_dir.is_dir():
        return global_data

    for path in data_dir.iterdir():
        # Skip directories
        if not path.is_file():
            continue
        # Skip unsupported file types
        if path.suffix not in DATA_LOADERS:
            logger.warning(f"Unsupported data file suffix '{path.suffix}': {path}")
            continue

        loader = DATA_LOADERS[path.suffix]

        try:
            with path.open("r", encoding="utf-8", newline="") as f:
                global_data[slugify(path.stem, separator="_")] = loader(f)
        except Exception as e:
            logger.error(f"Failed to parse data file '{path.name}': {e}")
            continue

    return global_data


def apply_page_transformations(pages: list[Page]) -> list[Page]:
    """
    Applies programmatic transformations to pages.
    """
    for page in pages:
        # Add "Links" tag to anything that might be missing it in the links directory
        if page["source_path"].parts[1] == "links":
            if "Links" not in page["tags"]:
                page["tags"].append("Links")
        elif page["source_path"].parts[1] == "recipes":
            if "Recipes" not in page["tags"]:
                page["tags"].append("Recipes")
        elif page["source_path"].parts[1] == "books":
            if "BookNotes" not in page["tags"]:
                page["tags"].append("BookNotes")

    return pages


def build_collections(pages: list[Page]) -> Collections:
    """
    Builds a 'collections' dictionary where the elements for each key are lists of pages. So {{ collections.pages }} or {{ collections.posts }}.

    Pages and posts with "hidden: true" in the frontmatter are stored with 'hidden_pages' and 'hidden_posts' keys.

    Pages are sorted by title. Posts are sorted by date.
    """

    collections: Collections = {
        "posts": [],
        "pages": [],
        "hidden_pages": [],
        "hidden_posts": [],
        "tags": defaultdict(list),
    }

    # Sort pages by date
    pages.sort(key=lambda x: x["date"], reverse=True)

    for page in pages:
        is_hidden = page.get("hidden", False)
        is_static_page = page.get("is_page", False)

        # Add posts and pages to the default collections
        if is_static_page:
            target = "hidden_pages" if is_hidden else "pages"
        else:
            target = "hidden_posts" if is_hidden else "posts"

        collections[target].append(page)

        # Create tag collections
        for tag in page["tags"]:
            collections["tags"][tag].append(page)

    # Sort page collections by title
    collections["pages"].sort(key=lambda x: x["title"])
    collections["hidden_pages"].sort(key=lambda x: x["title"])

    # Sort tags by count of pages
    collections["tags"] = dict(
        sorted(collections["tags"].items(), key=lambda item: len(item[1]), reverse=True)
    )

    # Print Status
    print("Collection Stats:")
    print(f" - posts: {len(collections['posts'])}")
    print(f" - pages: {len(collections['pages'])}")

    return collections


# endregion


# region writers
def clear_dist_dir(dist_dir: Path):
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    dist_dir.mkdir()


def copy_assets(assets_src: Path, dest_dir: Path):
    if not assets_src.exists():
        raise FileNotFoundError(f"Could not find assets source: {assets_src}")

    # Move to the output folder, NOT back into the source folder
    dest_assets = dest_dir / "assets"

    shutil.copytree(assets_src, dest_assets, dirs_exist_ok=True)
    print(f"📁 Assets mirrored to: {dest_assets}")


def build_search_index(site_dir: str | Path):
    # Get a str version of the dist dir.
    if isinstance(site_dir, Path):
        site = str(site_dir.resolve())
    else:
        site = str(site_dir)

    # python3 -m pagefind --site public --serve
    subprocess.run(["npx", "-y", "pagefind", "--site", site], check=True)


def get_relative_dest_path(page: Page) -> Path:
    """Calculates where the file should be written in the dist folder."""

    permalink = page["permalink"]
    if permalink.endswith("/"):
        return Path(permalink.strip("/")) / "index.html"
    return Path(permalink.lstrip("/"))


def write_build_stats(config: Config, collections: Collections, build_time: float):
    # Calculate the build size
    build_size_bytes = sum(
        f.stat().st_size for f in config.dist_dir.rglob("*") if f.is_file()
    )
    build_size_mb = build_size_bytes / (1024 * 1024)

    # Get the build stats
    build_stats = {
        "build_date": f"{datetime.datetime.now(ZoneInfo('America/Los_Angeles'))}",
        "python_version": sys.version.split()[0],
        "build_time_s": round(build_time, 2),
        "build_size_mb": round(build_size_mb, 1),
        "content": {
            "pages": len(collections["pages"]),
            "hidden_pages": len(collections["hidden_pages"]),
            "posts": len(collections["posts"]),
            "hidden_posts": len(collections["hidden_posts"]),
        },
    }

    file_path = config.dist_dir / "stats.json"
    with open(file_path, "w") as f:
        json.dump(build_stats, f, indent=2)


def write_pages(
    config: Config, site_data: dict, pages: list[Page], collections: Collections
):
    """Write all the pages to the destination directory."""
    for page in pages:
        context = {
            **site_data,
            **page,
            "collections": collections,
            "build_date": datetime.date.today(),
        }

        # Perform Jinja render step on markdown files if renderJinja flag is set
        if page.get("renderJinja") and page["source_path"].suffix == ".md":
            template = config.env.from_string(page["content"])
            page["content"] = template.render(**context)
            context = {**context, "content": page["content"]}

        # Render the page
        if page["layout"]:
            template = config.env.get_template(page["layout"])
        else:
            template = config.env.from_string(page["content"])

        # Write the page out
        dest_path = config.dist_dir / get_relative_dest_path(page)
        safe_write(file_path=dest_path, content=template.render(**context))


def write_tag_pages(
    config: Config, site_data: dict, pages: list[Page], collections: Collections
):
    """Write all the tag pages to the destination directory."""
    print("One day we'll write out some tag pages")


def build_site(config: Config, index: bool = False) -> float:
    start_time = time.time()
    print("🚀 Building site...")

    # Clear destination directory
    clear_dist_dir(config.dist_dir)

    # static assets copy
    copy_assets(assets_src=config.assets_dir, dest_dir=config.dist_dir)

    # load data files
    site_data = discover_data(config.data_dir)

    # Discover all pages and Transform files into dicts
    pages = [load_page(f) for f in discover_pages(config.src_dir)]
    page_count = len(pages)

    # Transform Pages
    pages = apply_page_transformations(pages)

    # Render page content
    for page in pages:
        if page["source_path"].suffix == ".md":
            page["content"] = md_to_html(page["raw_content"])
        else:
            page["content"] = page["raw_content"]

    # Create collections from pages
    collections = build_collections(pages=pages)

    # Write pages
    write_pages(config=config, site_data=site_data, pages=pages, collections=collections)
    # Write tag pages
    write_tag_pages(
        config=config, site_data=site_data, pages=pages, collections=collections
    )

    build_duration = time.time() - start_time

    # Write build stats
    write_build_stats(config=config, collections=collections, build_time=build_duration)

    print(f"✅ Build finished in {build_duration:.3f}s. Processed {page_count} pages.")

    # Run pagefind
    if index:
        build_search_index(config.dist_dir)
        # Final Duration
        final_duration = time.time() - start_time
        print(f"✅ Search index finished, {final_duration:.3f}s.")

    return build_duration
