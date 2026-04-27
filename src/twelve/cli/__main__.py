from __future__ import annotations

from argparse import ArgumentParser
from collections.abc import Sequence

from twelve.cli.build import setup_build_subparser
from twelve.cli.new import setup_new_subparser
from twelve.cli.stash import setup_stash_subparser
from twelve.cli.tool import setup_tool_subparser
from twelve.cli.utils import CLI_FORMATTER


def cli(argv: Sequence[str] | None = None) -> int:

    main_parser = ArgumentParser(description="Twelve:", formatter_class=CLI_FORMATTER)

    # Create the top-level subparser object
    command_parser = main_parser.add_subparsers(dest="command")

    # create the parser for the "stash" command
    setup_stash_subparser(command_parser)
    setup_build_subparser(command_parser)
    setup_new_subparser(command_parser)
    setup_tool_subparser(command_parser)

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

    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
