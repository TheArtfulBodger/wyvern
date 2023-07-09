"""Minimal Downloader."""

import importlib
import logging
from argparse import ArgumentParser, Namespace

import coloredlogs

from wyvern.abstract import Artisan, Factory
from wyvern.minimal.manager import MinimalManager


def make_parser(parser: ArgumentParser) -> None:
    """
    Create The Parser.

    This allows use of subcommands.
    """
    parser.add_argument(
        "downloader",
        type=str,
        help="The Downloader class (Factory or Artisan)",
    )
    parser.add_argument(
        "job_str",
        type=str,
        help="The String to pass into the artisan",
        nargs="?",
    )


def run_main(args: Namespace) -> None:
    """
    Run the main function.

    :param args: The Parsed Arguments
    """
    coloredlogs.install(
        level="INFO",
        fmt="[%(asctime)s] %(levelname)s - %(message)s",
    )

    try:
        module_name, class_name = args.downloader.rsplit(".", 1)
    except ValueError:
        logging.exception("Downloader must contain module and class")

    try:
        module = importlib.import_module(module_name)
        class_constructor = getattr(module, class_name)
    except ImportError:
        logging.exception("Cannot load module %s", module_name)
        return
    except AttributeError:
        logging.exception("Cannot find class %s in %s", class_name, module_name)
        return

    try:
        creator = class_constructor()
    except TypeError:
        logging.exception(
            "%s encountered an error in the constructor. This is normally if"
            "the constructor takes arguments.",
            class_name,
        )
        return

    manager = MinimalManager(creator.plugin_id)

    if isinstance(creator, Factory):
        logging.info("Loading jobs from %s", class_name)
        creator.load_jobs(manager)
    elif isinstance(creator, Artisan):
        if args.job_str is None:
            logging.error("Job string cannot be none for an artisan.")
            return
        logging.info("Loading job from %s", class_name)
        manager.add_job(creator.request_job(manager, args.job_str))
    else:
        logging.exception("%s is not an Artisan or a Factory", class_name)

    manager.do_jobs()


def main(name: str | None = None) -> None:
    """
    Run the Minimal Downloader.

    usage: python -m wyvern.minimal [-h] downloader [job_str]

    Run The Minimal Downloader

    positional arguments:
      downloader  The Downloader class (Factory or Artisan)
      job_str     The String to pass into the artisan

    options:
      -h, --help  show this help message and exit
    """
    parser = ArgumentParser(prog=name, description="Run The Minimal Downloader")

    make_parser(parser)

    args = parser.parse_args()
    run_main(args)
