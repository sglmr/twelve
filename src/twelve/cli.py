from __future__ import annotations

import webbrowser
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser, Namespace
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from urllib import parse

from jinja2 import Template
from rich import print
from slugify import slugify

from twelve.generator import Config, build_site


# region new
def parse_new(args: Namespace, parser: ArgumentParser):
    # List the template choices

    config = Config(src_dir=Path(args.input), dist_dir=Path(args.input))

    new_template_choices = [t for t in config.template_dir.glob("*.md")]

    if args.list:
        print("Available Templates:")
        for t in new_template_choices:
            print(f" - {t.stem}")

    # Preview a specific template
    elif args.template and args.preview:
        file = next(config.template_dir.glob(f"*{args.template}*.md"))
        print(file.read_text().strip())

    # Create a new file with the specified template
    elif args.template:
        if isinstance(args.title, str):
            title = args.title
        else:
            title = " ".join(args.title)

        template = next(config.template_dir.glob(f"*{args.template}*.md"))
        context = {
            "date": args.date.date().isoformat(),
            "title": title,
            "slug": slugify(title),
            "template_name": template.name,
            "permalink": f"/blog/{slugify(title)}/",
        }

        jinja_template = Template(template.read_text())
        rendered = jinja_template.render(**context)

        dist = (
            config.src_dir
            / f"{template.stem}s"
            / str(args.date.year)
            / f"{slugify(title)}.md"
        )

        # Write the file
        if dist.exists():
            raise ValueError("Oops, almost overwrote an existing file, try again")
        dist.write_text(rendered)

        # Open the file in obsidian
        encoded_file = parse.quote(str(dist))

        # uri = f"obsidian://open?vault={encoded_vault}&file={encoded_file}"
        uri = f"obsidian://open?file={encoded_file}"
        webbrowser.open(uri)

    else:
        parser.print_help()


# endregion


# region build
def parse_build(args: Namespace, parser: ArgumentParser):
    config = Config(src_dir=Path(args.input), dist_dir=Path(args.output))
    build_duration = build_site(config=config)

    if args.serve or args.live_reload:
        from livereload import Server

        server = Server()
    if args.live_reload:

        def _rebuild():
            build_site(config=config)

        server.watch(str(config.src_dir), _rebuild)
    if args.serve or args.live_reload:
        server.serve(
            root=str(config.dist_dir),
            port=8080,
            open_url_delay=build_duration * 1.05,
        )


# endregion


# region cli
def cli(argv: Sequence[str] | None = None) -> int:
    parser = ArgumentParser(
        description="bs: build site", formatter_class=ArgumentDefaultsHelpFormatter
    )

    # Create the top-level subparser object
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- BUILD COMMAND ---
    build_parser = subparsers.add_parser("build", help="Build the static site")

    build_parser.add_argument(
        "-i",
        "--input",
        dest="input",
        default="content",
        help="Where to look for source content.",
        required=True,
    )
    build_parser.add_argument(
        "-o",
        "--output",
        dest="output",
        default="_site",
        help="Where the finished site will write to.",
        required=True,
    )
    build_parser.add_argument("-s", "--serve", action="store_true", help="Serve site")
    build_parser.add_argument(
        "-l", "--live-reload", action="store_true", help="Live reload"
    )

    # --- NEW COMMAND ---
    new_parser = subparsers.add_parser("new", help="Create new content")
    new_parser.add_argument(
        "template", nargs="?", help="The name of a template to create content from."
    )
    new_parser.add_argument("title", nargs="*", default="New Post", help="title")
    new_parser.add_argument("-l", "--list", action="store_true", help="list templates")
    new_parser.add_argument(
        "-p", "--preview", action="store_true", help="preview template"
    )
    new_parser.add_argument("-d", "--date", default=datetime.today(), help="post date")

    # --- CRAWL COMMAND ---
    crawl_parser = subparsers.add_parser("crawl", help="Crawl the website.")
    crawl_parser.add_argument("url", help="url to crawl")
    crawl_parser.add_argument(
        "-l", "--links", action="store_true", help="check for dead links"
    )

    # Parse args
    args = parser.parse_args(argv)

    match args.command:
        case "build":
            parse_build(args, build_parser)
        case "new":
            parse_new(args, new_parser)
        case "crawl":
            print("Not implemented yet")

    return 0


# endregion
