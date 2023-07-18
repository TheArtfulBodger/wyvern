"""
Youtube DL Artisan and Job.

Contains classes for downloading videos via yt-dlp.
"""

from contextlib import suppress
from logging import Logger

from yt_dlp import YoutubeDL

from wyvern.abstract import Artisan, Job, Manager


class YtdlpJob(Job):
    """
    Create a job that is executed by yt-dlp.

    :param url: The URL of the video to download
    :param name: The name to show in the UI - Will get overridden in
                 meth:`progress_callback`
    :param kwargs: Additional parameters to add.
    """

    def __init__(
        self: "YtdlpJob",
        url: str,
        name: str | None = None,
        **kwargs: dict,
    ) -> "YtdlpJob":
        """Job Constructor. Sets required Variables."""
        self.url = url
        if name is None:
            self.name = url
        else:
            self.name = name
        self.args = kwargs

        # Add callbacks and logger to self.args
        self.logger = Logger(name="ytdlp")
        self.args["logger"] = self.logger

        if "progress_hooks" not in self.args:
            self.args["progress_hooks"] = []
        self.args["progress_hooks"].append(lambda x: self.progress_callback(x))

    def should_skip(self: "YtdlpJob", _: Manager) -> bool:
        """Return True as yt-dlp will handle this checking for us."""
        return False

    def do_download(self: "YtdlpJob", _: Manager) -> None:
        """Run the download job."""
        with YoutubeDL(self.args) as ydl:
            ydl.download(self.url)

    def progress_callback(self: "YtdlpJob", data: dict) -> None:
        """Update state from job progress."""
        with suppress(KeyError):
            self.name = data["info_dict"]["title"]
        try:
            tb = 0
            if "total_bytes" in data:
                tb = data["total_bytes"]
            elif "total_bytes_estimate" in data:
                tb = data["total_bytes_estimate"]
            self.progress = data["downloaded_bytes"] / tb
        except (KeyError, ZeroDivisionError, TypeError):
            self.progress = 0

        verb = data["status"].title()
        if data["info_dict"]["protocol"] != "https":
            thing = data["info_dict"]["protocol"].replace("_", " ").title()
        else:
            thing = data["info_dict"]["ext"].upper()
        if "name" in data["info_dict"]:
            name = data["info_dict"]["name"]
        else:
            name = data["filename"]
        self.status = f"{verb} {thing}: {name}"

        self.updated.set()


class YtdlpArtisan(Artisan):
    """
    Youtube Artisan.

    Request the Download of a singular youtube video.
    """

    plugin_id = "youtube"

    def request_job(self: "YtdlpArtisan", _: Manager, job_str: str) -> Job:
        """
        Create the job object.

        :todo: Allow for options to be specified alongside the URL as either a
               JSON object or additional URL-encoded parameters
        :param job_str: The URL of the video to download.
        """
        return YtdlpJob(
            job_str,
            extract_flat="discard_in_playlist",
            fragment_retries=10,
            ignoreerrors="only_download",
            postprocessors=[
                {
                    "key": "FFmpegConcat",
                    "only_multi_video": True,
                    "when": "playlist",
                },
            ],
            retries=10,
            outtmpl=f"{self.plugin_id}/%(title)s [%(id)s].%(ext)s",
        )
