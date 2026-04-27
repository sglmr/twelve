import argparse
import subprocess

from rich import print

from twelve.cli.utils import CLI_FORMATTER, print_title


def upgrade_self():
    print("Checking for updates and syncing dependencies...")
    try:
        # We call 'uv tool upgrade' specifically for your package name
        subprocess.run(["uv", "tool", "upgrade", "twelve"], check=True)
        print("Upgrade successful!")
    except subprocess.CalledProcessError as e:
        print(f"Upgrade failed: {e}")
    except FileNotFoundError:
        print("Error: 'uv' is not installed or not in your PATH.")


def handle_tool(args: argparse.Namespace) -> None:
    """Coordinator function for args."""

    steps = 0

    if args.upgrade:
        print_title("Self Upgrade")
        upgrade_self()
        steps += 1

    if steps == 0:
        args.parser.print_help()


def setup_tool_subparser(subparser: argparse._SubParsersAction) -> None:
    """Configures the 'tool' command and attaches it to the main subparsers."""

    tool_p = subparser.add_parser(
        "tool", help="Perform actions on the script", formatter_class=CLI_FORMATTER
    )
    tool_p.add_argument("-u", "--upgrade", action="store_true", help="self upgrade")

    # Pro Tip: Set a 'func' default so main() knows who to call
    tool_p.set_defaults(func=handle_tool, parser=tool_p)
