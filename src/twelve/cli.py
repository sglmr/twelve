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

from twelve.generator import Config, build_site
from twelve.utils import safe_write


def template_choices(templates_dir: Path) -> list[str]:

    return [t.stem for t in templates_dir.glob("*.md")]


def print_template_choices(templates_dir: Path):
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


def run_build_site(input: Path, output: Path, index: bool) -> float:
    print("🚀 Building site...")
    start_time = time.time()
    config = Config(src_dir=input, dist_dir=output)
    build_site(config=config, index=index)
    duration = time.time() - start_time
    print(f"🏁 Build completed in {duration:.1f}s")
    return duration


def run_build_and_serve(
    input: Path, output: Path, reload: bool, index: bool, port: int = 8080
):

    abs_input = input.resolve()
    abs_output = output.resolve()

    def _build():
        return run_build_site(input=abs_input, output=abs_output, index=index)

    def _ignore(path_str):
        # Resolve the incoming path from livereload
        path = Path(path_str).resolve()

        # Use is_relative_to to check location
        if path.is_relative_to(abs_output):
            return True

        # Ignore other hidden files like .DS_Store or .git
        if any(
            part.startswith(".")
            for part in path.parts
            if part not in [abs_input.name, abs_output.name]
        ):
            if not path.is_relative_to(
                abs_input
            ):  # Don't ignore files in the root input if they aren't hidden
                return True

        return False

    duration = _build()
    server = Server()
    if reload:
        server.watch(filepath=str(abs_input), delay=1, func=_build, ignore=_ignore)
    server.serve(
        root=str(output),
        port=8080,
        open_url_delay=0,
    )


# endregion


# region cli
def cli(argv: Sequence[str] | None = None) -> int:

    env_input = os.getenv("TWELVE_INPUT")
    env_output = os.getenv("TWELVE_OUTPUT", ".site")

    main_parser = ArgumentParser(
        description="bs: build site", formatter_class=ArgumentDefaultsHelpFormatter
    )

    # A shared parser for the input directory
    shared_parser = ArgumentParser(add_help=False)
    # shared_parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output.")
    shared_parser.add_argument(
        "-i", "--input", dest="input", help="input directory", default=env_input
    )

    # Create the top-level subparser object
    subparsers = main_parser.add_subparsers(dest="command", help="Available commands")

    # --- BUILD COMMAND ---
    build_parser = subparsers.add_parser(
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
        "--index", action="store_true", help="Build pagefind search index"
    )

    # --- NEW COMMAND ---
    new_parser = subparsers.add_parser(
        "new", parents=[shared_parser], help="Create a new post"
    )
    new_parser.add_argument(
        "template", nargs="?", help="The name of a template to create content from."
    )
    new_parser.add_argument("title", nargs="?", default="New Post", help="title")
    new_parser.add_argument("-l", "--list", action="store_true", help="list templates")

    # --- CRAWL COMMAND ---
    crawl_parser = subparsers.add_parser("crawl", help="Crawl the website.")
    crawl_parser.add_argument("url", help="url to crawl")
    crawl_parser.add_argument(
        "-l", "--links", action="store_true", help="check for dead links"
    )

    # Parse args
    args = main_parser.parse_args(argv)
    input_path = Path(args.input)

    match args.command:
        case "build":
            output_path = Path(args.output)
            if args.live_reload or args.serve:
                run_build_and_serve(
                    input=input_path,
                    output=output_path,
                    reload=args.live_reload,
                    index=args.index,
                )
            else:
                run_build_site(input=input_path, output=output_path, index=args.index)

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
