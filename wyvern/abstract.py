"""Abstract Classes Module.

Contains the abstract classes used by the project.

* :class:`~DataStore`
* :class:`~Artisan`
* :class:`~Factory`
* :class:`~Job`
* :class:`~Manager`
"""
from abc import ABC, abstractmethod
from queue import Queue
from threading import Event


class DataStore(ABC):
    """Data Store Class.

    :param plugin_id: The ID of the Factory or Artisan providing jobs.
    :param config_str: The configuration string (meaning defined by
        inheriting constructor.)

    This class is mainly for type hinting with the following defined.

    * :func:`__getitem__` Get the stored value.
    * :func:`__setitem__` Set the stored value

    These functions should call to the store directly (without caching). This
    avoids the case where there are multiple nodes downloading causing a race
    condition.
    """

    @abstractmethod
    def __init__(
        self: "DataStore",
        plugin_id: str,
        config_str: str,
    ) -> "DataStore":
        """Create the object."""

    @abstractmethod
    def __getitem__(
        self: "DataStore",
        key: str,
    ) -> str:
        """Get the stored value."""

    @abstractmethod
    def __setitem__(
        self: "DataStore",
        key: str,
        value: str,
    ) -> None:
        """Store the value."""


class Job(ABC):
    """Job Base Class.

    This class represents a job's data.
    """

    name: str
    """The Name of the job (should be displayed in the UI)"""

    url: str | None
    """URL of the job."""

    status: str | Exception
    """
    Status during the Download (eg Downloading, Extracting etc), or if the job
    failed, the exception it raised.
    """

    updated: Event = Event()
    """Event to be called when the externally visible members are updated."""

    sub_jobs: Queue["Job"] | None
    """
    Sub Jobs Created as part of the job processing.

    Jobs may be added to the queue before the current job has completed. Care
    should be taken to avoid race conditions on secrets or filesand depth-first
    themed non-terminations.
    """

    progress: float = 0.0
    """The progress through the download. Valid values are between 0 and 1"""

    @abstractmethod
    def do_download(self: "Job", manager: "Manager") -> None:
        """
        Run the download.

        This function will execute the download of the job, updating
        :attr:`status` and :attr:`progress` as appropriate.
        """

    @abstractmethod
    def should_skip(self: "Job", manager: "Manager") -> bool:
        """
        Work out if the job should be skipped.

        This should check if the file already exists in the destination folder.
        """


class Manager(ABC):
    """Manager Class.

    The :attr:`configuration` and :attr:`secrets` variables are specific to the
    :class:`~Factory` or
    :class:`~Artisan` which created the job.
    """

    configuration: DataStore
    """Variables affecting how download jobs are processed.

    These are straightforward nonsensitive variables. Examples include:

    * Bitrate to download at
    * URL to site
    """

    secrets: DataStore
    """More sensitive variables.

    These should be obfuscated in any UI and stored more securely. Examples
    include:

    * API Keys
    * Passwords
    * Cookie Values
    """

    plugin_id: str
    """The calling Artisan or Factory's :attr:`~Factory.plugin_id`"""

    @abstractmethod
    def add_job(self: "Manager", job: Job | None) -> None:
        """
        Add a job object to the queue.

        This will add to the queue of jobs to be executed directly after this.
        """


class Artisan(ABC):
    """Artisan Base Class.

    This class creates a singular job based off of a request (eg
    downloading a specific video from a site)
    """

    plugin_id: str
    """
    ID of the plugin to use

    Should be in kebab-case. Will be the name of the folder files are output
    into. The name may be shared with Artisans, but should only be shared with
    one :class:`~Factory`.
    """

    @abstractmethod
    def request_job(
        self: "Artisan",
        manager: Manager,
        job_str: str,
    ) -> Job | None:
        """
        Request a Job from the job_str (often a URL or an ID).

        If the job cannot be found, return None.
        """


class Factory(ABC):
    """Factory Base Class.

    This class creates a number of jobs (eg downloading all owned
    products on a site)
    """

    plugin_id: str
    """
    ID of the plugin to use

    Should be in kebab-case. Will be the name of the folder files are output
    into. The name should be unique per-Factory, but may be shared with one
    (or more) :class:`~Artisan`.
    """

    @abstractmethod
    def load_jobs(self: "Factory", manager: Manager) -> None:
        """Load the jobs.

        This is the main function of the downloader. It loads in jobs from the
        source and adds them to the queue with :func:`~Manager.add_job`. These
        jobs can be jobs to load in more jobs, but this practice should be
        avoided if at all possible. Adding jobs should be designed in such a
        way that a job can be starting to be downloaded while later jobs are
        being added (eg loading in later pages of results).
        """
