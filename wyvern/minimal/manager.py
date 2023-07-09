"""Minimal Manager Class."""

import logging
import queue
from concurrent.futures import ThreadPoolExecutor
from time import sleep

from alive_progress import alive_bar

from wyvern.abstract import Job, Manager


class MinimalManager(Manager):
    """
    Minimal implementation of a manager.

    This class only supports jobs from one loader and is designed for use with
    the minimal program as a proof-of-concept for the project. It downloads one
    job at a time in a background thread, updating a console progress bar with
    the status.
    """

    def __init__(self: "MinimalManager", plugin_id: str) -> "MinimalManager":
        """
        Create the object.

        :param plugin_id: The ID of the Factory or Artisan providing jobs.
        """
        self.plugin_id = plugin_id
        self.job_queue = queue.Queue()

    def add_job(self: "MinimalManager", job: Job) -> None:
        """Add a job to the end of the queue."""
        self.job_queue.put(job)

    def do_jobs(self: "MinimalManager") -> None:
        """Run the jobs in a background thread, outputting a progress bar."""
        with ThreadPoolExecutor(max_workers=1) as executor:
            while not self.job_queue.empty():
                job = self.job_queue.get()
                logging.info("Downloading: %s", job.name)
                with alive_bar(manual=True, spinner="twirls") as bar:
                    fut = executor.submit(job.do_download, self)
                    while not fut.done():
                        bar(job.progress)
                        sleep(0.25)
                    bar(1.0)