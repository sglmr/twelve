from rich import print


def print_title(message: str, format: str = "bold cyan"):
    print(f"\n[{format}]{message}[/{format}]")
