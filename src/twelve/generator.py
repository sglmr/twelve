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
from jinja2 import Environment
from rich import print
from slugify import slugify

from twelve.config import get_jinja_env
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
    tags: list[str]
    description: NotRequired[str | None]
    layout: NotRequired[str | None]

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


Collections = dict[str, list[Page]]


def create_page_object(content: str, metadata: dict, source_path: Path) -> Page:
    """Creates a Page object from the content of a file."""
    permalink = str(metadata.get("permalink", ""))
    permalink = permalink if permalink.startswith("/") else f"/{permalink}"
    page: Page = {
        "title": metadata["title"],
        "date": metadata.get("date", datetime.date.today()),
        "permalink": permalink,
        "tags": normalize_tags(metadata.get("tags")),
        "layout": metadata.get("layout"),
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
def is_valid_content_file(path: Path, input: Path) -> bool:
    """Decides if the file at a path should be considered "content" to build the site.
    1. The path is a file
    2. The file extension is a PARSEABLE_EXTENSION
    3. The parent folder doesn't start with an underscore (i.e. not "_data")
    4. The parent folder doesn't start with a '.' (i.e. not ".obsidian")
    5. The filename doesn't start with a '.' (i.e. not ".DS_Store")
    """

    # Skip non-files
    if not path.is_file():
        return False

    # Skip unsported file extensions
    if path.suffix not in PARSEABLE_EXTENSIONS:
        return False

    # Check if any parent (relative to src) starts with '_'
    relative_parts = path.relative_to(input)
    filename = relative_parts.parts[-1]
    dirs = relative_parts.parts[:-1]

    # Skip anything in the assets directory
    if dirs[0] == "assets":
        return False

    # Skip any directories that starts with "_" or "."
    for dir in dirs:
        if dir.startswith("_"):
            return False
        elif dir.startswith("."):
            return False

    # Skip any filenames that start with "."
    if filename.startswith("."):
        return False

    # It's a valid file
    return True


def discover_content(input: Path) -> Generator[Path, None, None]:
    """
    Crawls the input_dir, excluding any files that shouldn't or can't
    be processed.
    """
    for file in input.rglob("*"):
        if is_valid_content_file(path=file, input=input):
            logger.debug(f"Content discovery including '{file.relative_to(input)}'")
            yield file
        else:
            logger.debug(f"Content discovery skipping '{file.relative_to(input)}'")


def is_valid_data_file(path: Path, input: Path):
    """Decides if the file at a path is a proessable 'data' file to build the site with.
    1. The path is a file
    """
    # Skip non-files
    if not path.is_file():
        return False

    # Skip files that don't have a data loader
    if path.suffix not in DATA_LOADERS:
        logger.error(
            f"No DATA_LOADER for data '{path.suffix}' files: {path.relative_to(input)}"
        )
        return False

    # It's a valid file
    return True


def discover_data_files(input: Path) -> dict[str, Any]:
    """Discover and parse the contents of data files into dictionaries."""

    data_dir = input / "_data"
    global_data: dict[str, Any] = {}

    for path in data_dir.rglob("*"):
        # Skip unprocessable data files
        if not is_valid_data_file(path, input):
            continue

        loader = DATA_LOADERS[path.suffix]

        # Try to load (parse) the file
        try:
            with path.open("r", encoding="utf-8", newline="") as f:
                global_data[slugify(path.stem, separator="_")] = loader(f)
        except Exception as e:
            logger.error(f"Failed to parse data file '{path.relative_to(input)}': {e}")
            continue

    return global_data


def build_collections(pages: list[Page]) -> Collections:
    """
    Builds a 'collections' dictionary where the elements for each key are lists of content objects.
    Collection keys are "tags" from the frontmatter/metadata.
    They are all available in templates as {{ collections.pages }} or {{ collections.posts }} or {{ collections["book-notes"] }}.

    """

    # Sort pages by date
    pages.sort(key=lambda x: x["date"], reverse=True)

    # Build collections from page tags
    collections: Collections = defaultdict(list)
    for page in pages:
        collections[all].append(page)
        for tag in page["tags"]:
            collections[tag].append(page)

    # Sort collections by count of pages in descending order
    sorted_collections = sorted(
        collections.items(), key=lambda item: len(item[1]), reverse=True
    )
    # Convert the list back into a dictionary
    collections = dict(sorted_collections)

    return collections


# endregion


# region writers
def clear_output_dir(output: Path):
    """Delete the output directory."""
    if output.exists():
        shutil.rmtree(output)
    while output.exists():
        time.sleep(0.0001)
    logger.info(f"Deleted output dir '{output}'")
    output.mkdir()


def copy_assets(input: Path, output: Path):
    """Copy assets into the output directory."""

    input_assets = input / "assets"
    dest_assets = output / "assets"
    shutil.copytree(input_assets, dest_assets, dirs_exist_ok=True)
    logger.info(f"📁 Assets mirrored to: {dest_assets}")


def build_search_index(site_dir: str | Path, quiet: bool):
    # Get a str version of the dist dir.
    site = str(site_dir)

    command = ["npx", "-y", "pagefind", "--site", site]
    if quiet:
        command.append("--quiet")

    # Run command
    subprocess.run(command, check=True)


def get_relative_dest_path(page: Page) -> Path:
    """Calculates where the file should be written in the dist folder."""

    permalink = page["permalink"]
    if permalink.endswith("/"):
        return Path(permalink.strip("/")) / "index.html"
    return Path(permalink.lstrip("/"))


def write_build_stats(output: Path, collections: Collections, build_time: float):
    # Calculate the build size
    build_size_bytes = sum(f.stat().st_size for f in output.rglob("*") if f.is_file())
    build_size_mb = build_size_bytes / (1024 * 1024)

    page_count = sum(1 for _ in output.rglob("index.html"))

    # Get the build stats
    build_stats = {
        "build_date": f"{datetime.datetime.now(ZoneInfo('America/Los_Angeles'))}",
        "python_version": sys.version.split()[0],
        "build_time_s": round(build_time, 2),
        "build_size_mb": round(build_size_mb, 1),
        "page_count": page_count,
    }

    file_path = output / "stats" / "index.html"
    safe_write(file_path=file_path, content=json.dumps(build_stats, indent=2))


def write_pages(
    output: Path,
    jinja_env: Environment,
    site_data: dict,
    pages: list[Page],
    collections: Collections,
):
    """Write all the pages to the destination directory."""
    common_context = {}
    common_context.update(site_data)  # Lowest priority
    common_context["build_date"] = (
        datetime.date.today()
    )  # TODO: maybe remove this one day?
    common_context["collections"] = collections

    for page in pages:
        # Build the context for a page
        context = common_context.copy()
        context["page"] = page
        context.update(page)

        # Perform Jinja render step on markdown files if renderJinja flag is set
        if page.get("renderJinja") and page["source_path"].suffix == ".md":
            template = jinja_env.from_string(page["content"])
            page["content"] = template.render(**context)
            context = {**context, "content": page["content"]}

        # Render the page
        if page["layout"]:
            template = jinja_env.get_template(page["layout"])
        else:
            template = jinja_env.from_string(page["content"])

        # Write the page out
        dest_path = output / get_relative_dest_path(page)
        safe_write(file_path=dest_path, content=template.render(**context))


def write_tag_pages(
    output: Path,
    jinja_env: Environment,
    site_data: dict,
    pages: list[Page],
    collections: Collections,
):
    """Write all the tag pages to the destination directory."""
    print("One day we'll write out some tag pages")


def build_site(input: Path, output: Path, index: bool = False, quiet=False) -> float:
    start_time = time.time()

    # Load jinja2 Environment
    jinja_env = get_jinja_env(input=input, version=start_time)

    # Clear destination directory
    clear_output_dir(output=output)

    # static assets copy
    copy_assets(input=input, output=output)

    # load data files
    site_data = discover_data_files(input=input)

    # Discover all pages and Transform files into dicts
    pages = [load_page(f) for f in discover_content(input)]

    logger.info(f"Discovered {len(pages)} content pages)")

    # Transform Pages

    # Render page content
    for page in pages:
        if page["source_path"].suffix == ".md":
            page["content"] = md_to_html(page["raw_content"])
        else:
            page["content"] = page["raw_content"]

    # Create collections from pages
    collections = build_collections(pages=pages)

    # Write pages
    write_pages(
        output=output,
        jinja_env=jinja_env,
        site_data=site_data,
        pages=pages,
        collections=collections,
    )

    # Write tag pages
    write_tag_pages(
        output=output,
        jinja_env=jinja_env,
        site_data=site_data,
        pages=pages,
        collections=collections,
    )

    build_duration = time.time() - start_time

    # Write build stats
    write_build_stats(output=output, collections=collections, build_time=build_duration)

    # Run pagefind
    if index:
        build_search_index(site_dir=output, quiet=quiet)
        # Final Duration

    return build_duration
