"""Minimal Manager Class."""

import logging
from concurrent.futures import ThreadPoolExecutor
from itertools import count
from queue import PriorityQueue

from alive_progress import alive_bar

from wyvern.abstract import DataStore, Job, Manager


class MinimalManager(Manager):
    """
    Minimal implementation of a manager.

    This class only supports jobs from one loader and is designed for use with
    the minimal program as a proof-of-concept for the project. It downloads one
    job at a time in a background thread, updating a console progress bar with
    the status.
    """

    def __init__(
        self: "MinimalManager",
        plugin_id: str,
        constructor: type[DataStore],
    ) -> "MinimalManager":
        """
        Create the object.

        :param plugin_id: The ID of the Factory or Artisan providing jobs.
        """
        self.plugin_id = plugin_id
        self.job_queue: PriorityQueue[(int, int, Job)] = PriorityQueue()
        self.configuration = constructor(plugin_id, "configuration.yaml")
        self.secrets = constructor(plugin_id, "secrets.yaml")
        self.unique = count()

    def add_job(self: "MinimalManager", job: Job | None) -> None:
        """Add a job to the end of the queue."""
        if Job:
            self.job_queue.put((0, next(self.unique), job))

    def do_jobs(self: "MinimalManager") -> None:
        """Run the jobs in a background thread, outputting a progress bar."""
        logging.info(
            "Starting to process jobs. There are %d jobs in the queue.",
            self.job_queue.qsize(),
        )

        with ThreadPoolExecutor(max_workers=1) as executor:
            while not self.job_queue.empty():
                priority, _, job = self.job_queue.get()
                if job.should_skip(self):
                    logging.info("Skipping: %s", job.name)
                    continue
                self._process_job(job, priority, executor)

    def _process_job(
        self: "MinimalManager",
        job: Job,
        priority: int,
        executor: ThreadPoolExecutor,
    ) -> None:
        def do_job() -> None:
            job.do_download(self)
            job.updated.set()

        logging.info("Downloading: %s", job.name)
        with alive_bar(
            manual=True,
            dual_line=True,
            title_length=40,
        ) as bar:
            fut = executor.submit(do_job)
            while not fut.done():
                job.updated.wait()
                job.updated.clear()

                # Update Statuses
                bar(job.progress)
                bar.text = getattr(job, "status", "")
                bar.title = job.name
                self._add_subjobs(job, priority)

            if fut.exception() is not None:
                logging.exception(fut.exception())

    def _add_subjobs(self: "MinimalManager", job: Job, priority: int) -> None:
        while getattr(job, "sub_jobs", None) and not job.sub_jobs.empty():
            self.job_queue.put(
                (
                    priority - 1,
                    next(self.unique),
                    job.sub_jobs.get(),
                ),
            )
