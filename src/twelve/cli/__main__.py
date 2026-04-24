from __future__ import annotations

import os
import sys
import webbrowser
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from urllib import parse

from jinja2 import Template
from rich import print
from slugify import slugify

from twelve.utils import safe_write

from .build import setup_build_subparser
from .stash import setup_stash_subparser


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
    command_parser = main_parser.add_subparsers(dest="command")

    # create the parser for the "stash" command
    setup_stash_subparser(command_parser)
    setup_build_subparser(command_parser)

    # create the parser fro the "new" command
    new_parser = command_parser.add_parser(
        "new", parents=[shared_parser], help="Create a new post"
    )
    new_parser.add_argument(
        "template", nargs="?", help="The name of a template to create content from."
    )
    new_parser.add_argument("title", nargs="?", default="New Post", help="title")
    new_parser.add_argument("-l", "--list", action="store_true", help="list templates")

    # --- CRAWL COMMAND ---
    crawl_parser = command_parser.add_parser("crawl", help="Crawl the website.")
    crawl_parser.add_argument("url", help="url to crawl")
    crawl_parser.add_argument(
        "-l", "--links", action="store_true", help="check for dead links"
    )

    # Parse args
    args = main_parser.parse_args(argv)

    # If you used parser.set_defaults(func=...), execute it:
    if hasattr(args, "func"):
        args.func(args)
    """
    if getattr(args.input):
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
        """

    return 0


# endregion


if __name__ == "__main__":
    cli()
