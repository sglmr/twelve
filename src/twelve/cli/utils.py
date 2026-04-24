from rich import print
from rich_argparse import RichHelpFormatter

CLI_FORMATTER = RichHelpFormatter


def print_title(message: str, format: str = "bold cyan"):
    print(f"\n[{format}]{message}[/{format}]")
