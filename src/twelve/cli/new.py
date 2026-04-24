import argparse
import os
import sys
import webbrowser
from datetime import datetime
from pathlib import Path
from urllib import parse

from jinja2 import Template
from rich import print
from slugify import slugify

from twelve.cli.utils import CLI_FORMATTER, print_title
from twelve.utils import safe_write

env_input = os.getenv("TWELVE_INPUT")
env_output = os.getenv("TWELVE_OUTPUT", ".site")


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


def handle_new(args: argparse.Namespace) -> None:
    """Coordinator function to manage the new content workflow."""
    input_path = Path(args.input).resolve()

    # List the available templates
    if args.list:
        print_title("Available Templates")
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

    args.parser.error("Missing 'title' or 'template'.")


def setup_new_subparser(subparser: argparse._SubParsersAction) -> None:
    """Configures the 'stash' command and attaches it to the main subparsers."""

    this_p = subparser.add_parser(
        "new", help="Create a new post", formatter_class=CLI_FORMATTER
    )
    this_p.add_argument(
        "template", nargs="?", help="The name of a template to create content from."
    )
    this_p.add_argument("title", nargs="?", help="title")
    this_p.add_argument("-l", "--list", action="store_true", help="list templates")
    this_p.add_argument(
        "-i",
        "--input",
        dest="input",
        help=f"input directory (default: {env_input})",
        default=env_input,
    )

    # Pro Tip: Set a 'func' default so main() knows who to call
    this_p.set_defaults(func=handle_new, parser=this_p)
