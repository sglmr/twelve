import argparse
import os
import time
from pathlib import Path

from livereload import Server
from rich import print

from twelve.cli.utils import CLI_FORMATTER, print_title
from twelve.generator import build_site

env_input = os.getenv("TWELVE_INPUT")
env_output = os.getenv("TWELVE_OUTPUT", ".site")


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


def handle_build(args: argparse.Namespace) -> None:
    """Coordinator function to manage the stashing workflow."""

    print_title("Building Site")

    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()
    _run_build(
        input=input_path,
        output=output_path,
        serve=args.serve,
        reload=args.live_reload,
        index=args.no_index is False,
        quiet=args.quiet,
    )


def setup_build_subparser(subparser: argparse._SubParsersAction) -> None:
    """Configures the 'stash' command and attaches it to the main subparsers."""

    build_p = subparser.add_parser(
        "build", help="Build the static site", formatter_class=CLI_FORMATTER
    )
    build_p.add_argument(
        "-o", "--output", dest="output", default=env_output, help="destination directory"
    )
    build_p.add_argument("-s", "--serve", action="store_true", help="Serve site")
    build_p.add_argument("-l", "--live-reload", action="store_true", help="Live reload")
    build_p.add_argument(
        "-n", "--no-index", action="store_true", help="do not build search index"
    )
    build_p.add_argument(
        "-i", "--input", dest="input", help="input directory", default=env_input
    )
    build_p.add_argument(
        "-q", "--quiet", dest="quiet", action="store_true", help="quiet mode"
    )

    # Pro Tip: Set a 'func' default so main() knows who to call
    build_p.set_defaults(func=handle_build, parser=build_p)
