from __future__ import annotations

import os
import sys
import time
import webbrowser
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from urllib import parse

from jinja2 import Template
from livereload import Server
from rich import print
from slugify import slugify

from twelve.generator import build_site
from twelve.utils import safe_write


def template_choices(templates_dir: Path) -> list[str]:
    """Returns a list of template options for creating new posts."""
    return [t.stem for t in templates_dir.glob("*.md")]


def print_template_choices(templates_dir: Path):
    """Print out a list of available templates to choose from."""
    print("Available templates: ")
    for t in template_choices(templates_dir):
        print(f" - {t}")


def get_template_content(template_name: str, templates_dir: Path) -> str:
    matches = list(templates_dir.glob(f"*{template_name}*.md"))

    if len(matches) > 1:
        names = ", ".join([m.name for m in matches])
        raise ValueError(f"Ambiguous template name! Found: {names}")
    if not matches:
        raise FileNotFoundError(
            f"Could not find template matching '{template_name}' in '{templates_dir}'"
        )
    return matches[0].read_text()


def create_post_data(
    title: str, template_name: str, template: str, date: datetime, input: Path
) -> tuple[str, Path]:
    """
    Creates the post content and where to write it to.
    """
    slug = slugify(title)

    context = {
        "date": date.date().isoformat(),
        "title": title,
        "slug": slugify(title),
        "permalink": f"/blog/{slug}/",
    }
    jinja_template = Template(template)
    post_content = jinja_template.render(**context)

    destination = input / f"{template_name}s" / str(date.year) / f"{slugify(title)}.md"

    return post_content, destination


# region new
def create_new_post(title: str, template_name: str, date: datetime, input: Path):
    try:
        template = get_template_content(
            template_name=template_name, templates_dir=input / "_templates"
        )

        post_content, destination = create_post_data(
            title=title,
            template_name=template_name,
            template=template,
            date=date,
            input=input,
        )

        safe_write(file_path=destination, content=post_content)

        # Open the file in obsidian
        # uri = f"obsidian://open?vault={encoded_vault}&file={encoded_file}"
        encoded_file = parse.quote(str(destination.relative_to(input)))
        uri = f"obsidian://open?file={encoded_file}"
        webbrowser.open(uri)
    except Exception as e:
        print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


# endregion


# region build


def should_ignore_watch_path(path_str: str, input: Path, output: Path) -> bool:
    """
    Helper function that decides if a changed file path should be ignored.
    True == ignore

    """
    # Resolve the incoming path from livereload
    path = Path(path_str).resolve()

    # Rule 1: ignore files in the output folder
    if path.is_relative_to(output):
        return True

    # Rule 2: Check if any part of the path is hidden (e.g., .git, .DS_Store, .obsidian/)
    #   any() to checks all parts of the path at once.
    if any(part.startswith(".") for part in path.parts):
        return True

    return False


def _run_build(
    input: Path,
    output: Path,
    serve: bool,
    reload: bool,
    index: bool,
    quiet: bool,
    port: int = 8080,
):
    def _build() -> float:
        print(f"🚀 Building site '{input}'")
        start_time = time.time()
        build_site(input=input, output=output, index=index, quiet=quiet)
        duration = time.time() - start_time
        print(f"🏁 Build completed in {duration:.1f}s")
        return duration

    def _ignore(path_str: str):
        return should_ignore_watch_path(path_str=path_str, input=input, output=output)

    duration = _build()

    # Early exit if not reloading or serving
    if not any([serve, reload]):
        return

    server = Server()
    if reload:
        server.watch(filepath=str(input), delay=1, func=_build, ignore=_ignore)
    server.serve(
        root=str(output),
        port=port,
        open_url_delay=0,
    )


# endregion


# region cli
def cli(argv: Sequence[str] | None = None) -> int:

    env_input = os.getenv("TWELVE_INPUT")
    env_output = os.getenv("TWELVE_OUTPUT", ".site")

    main_parser = ArgumentParser(
        description="Twelve:", formatter_class=ArgumentDefaultsHelpFormatter
    )

    # A shared parser for the input directory
    shared_parser = ArgumentParser(add_help=False)
    # shared_parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output.")
    shared_parser.add_argument(
        "-i", "--input", dest="input", help="input directory", default=env_input
    )
    shared_parser.add_argument(
        "-q", "--quiet", dest="quiet", action="store_true", help="quiet mode"
    )

    # Create the top-level subparser object
    command_parsers = main_parser.add_subparsers(dest="command")

    # create the parser for the "build" command
    build_parser = command_parsers.add_parser(
        "build", parents=[shared_parser], help="Build the static site"
    )
    build_parser.add_argument(
        "-o", "--output", dest="output", default=env_output, help="destination directory"
    )
    build_parser.add_argument("-s", "--serve", action="store_true", help="Serve site")
    build_parser.add_argument(
        "-l", "--live-reload", action="store_true", help="Live reload"
    )
    build_parser.add_argument(
        "-n", "--no-index", action="store_true", help="do not build search index"
    )

    # create the parser fro the "new" command
    new_parser = command_parsers.add_parser(
        "new", parents=[shared_parser], help="Create a new post"
    )
    new_parser.add_argument(
        "template", nargs="?", help="The name of a template to create content from."
    )
    new_parser.add_argument("title", nargs="?", default="New Post", help="title")
    new_parser.add_argument("-l", "--list", action="store_true", help="list templates")

    # --- CRAWL COMMAND ---
    crawl_parser = command_parsers.add_parser("crawl", help="Crawl the website.")
    crawl_parser.add_argument("url", help="url to crawl")
    crawl_parser.add_argument(
        "-l", "--links", action="store_true", help="check for dead links"
    )

    # Parse args
    args = main_parser.parse_args(argv)
    input_path = Path(args.input).resolve()

    match args.command:
        case "build":
            output_path = Path(args.output).resolve()
            _run_build(
                input=input_path,
                output=output_path,
                serve=args.serve,
                reload=args.live_reload,
                index=args.no_index is False,
                quiet=args.quiet,
            )

        case "new":
            # List the available templates
            if args.list:
                print_template_choices(input_path / "_templates")
                return
            # Create a new post
            if args.template and args.title:
                create_new_post(
                    title=str(args.title),
                    template_name=str(args.template),
                    date=datetime.now(),
                    input=input_path,
                )
                return
            new_parser.print_help()
        case "crawl":
            print("Not implemented yet")

    return 0


# endregion
