"""Minimal Downloader."""

from argparse import ArgumentParser

from .minimal import main as minimal_main


def main(name: str | None = None) -> None:
    """
    Run Wyvern Tools.

    usage: python -m wyvern [-h] {minimal} ...

    Run Wyvern Tools

    positional arguments:
      {minimal}   sub-command help
        minimal   Run The Minimal Downloader

    options:
        -h, --help  show this help message and exit
    """
    parser = ArgumentParser(prog=name, description="Run Wyvern Tools")

    subparsers = parser.add_subparsers(help="sub-command help", dest="cmd")

    minimal_parser = subparsers.add_parser(
        "minimal",
        help="Run The Minimal Downloader",
    )
    minimal_main.make_parser(minimal_parser)

    args = parser.parse_args()
    if args.cmd == "minimal":
        minimal_main.run_main(args)
