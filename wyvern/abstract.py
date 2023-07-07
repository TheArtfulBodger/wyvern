"""Abstract Classes Module.

Contains the abstract classes used by the project.

* :class:`~wyvern.abstract.DataStore`
* :class:`~wyvern.abstract.Artisan`
* :class:`~wyvern.abstract.Factory`
* :class:`~wyvern.abstract.Job`
* :class:`~wyvern.abstract.Manager`
"""
from abc import ABC, abstractmethod


class DataStore(ABC):
    """Data Store Class.

    This class is mainly for type hinting with the following defined.

    * :func:`__getitem__` Get the stored value.
    * :func:`__setitem__` Set the stored value

    These functions should call to the store directly (without caching). This
    avoids the case where there are multiple nodes downloading causing a race
    condition.
    """

    @abstractmethod
    def __getitem__(self: "DataStore", key: str) -> str:
        """Get the stored value."""

    @abstractmethod
    def __setitem__(self: "DataStore", key: str, value: str) -> None:
        """Store the value."""


class Job(ABC):
    """Job Base Class.

    This class represents a job's data.
    """

    name: str
    """The Name of the job (should be displayed in the UI)"""

    url: str | None
    """URL of the job."""

    status: str
    """Status during the Download (eg Downloading, Extracting etc)"""

    progress: float
    """The progress through the download.

    Valid values are between 0 and 1
    """


class Manager(ABC):
    """Manager Class.

    The :attr:`configuration` and :attr:`secrets` variables are specific to the
    :class:`~wyvern.abstract.factory.Factory` or
    :class:`~wyvern.abstract.artisan.Artisan` which created the job.
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

    @abstractmethod
    def add_job(self: "Manager", job: Job) -> None:
        """Add a Job object to the queue."""


class Artisan(ABC):
    """Artisan Base Class.

    This class creates a singular job based off of a request (eg
    downloading a specific video from a site)
    """

    @abstractmethod
    def request_job(self: "Artisan", manager: Manager, job_str: str) -> Job:
        """Request a Job from the job_str (often a URL or an ID)."""


class Factory(ABC):
    """Factory Base Class.

    This class creates a number of jobs (eg downloading all owned
    products on a site)
    """

    @abstractmethod
    def load_jobs(self: "Manager", manager: Manager) -> None:
        """Load the jobs.

        This is the main function of the downloader. It loads in jobs from the
        source and adds them to the queue with
        :func:`~wyvern.artisan.manager.Manager.add_job`. These
        jobs can be jobs to load in more jobs, but this practice should be
        avoided if at all possible. Adding jobs should be designed in such a
        way that a job can be starting to be downloaded while later jobs are
        being added (eg loading in later pages of results).
        """
