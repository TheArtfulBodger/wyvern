"""
Operavision Factory and Credits Job.

Download All Video Performances on operavision.eu
"""

import logging

import requests
from bs4 import BeautifulSoup

from wyvern.abstract import Factory, Manager
from wyvern.plugins.ytdlp import YtdlpJob


class OperaVisionFactory(Factory):
    """
    Operavision Factory.

    Download All Video Performances on operavision.eu
    """

    plugin_id = "operavision"

    def load_jobs(self: "OperaVisionFactory", manager: Manager) -> None:
        """Load the list of performances and populate the job queue."""
        # Get the list of performances
        try:
            rsp = requests.get(
                "https://operavision.eu/performances",
                timeout=10,
            )
        except requests.exceptions.Timeout:
            logging.exception("Timeout when Loading URL")
        soup = BeautifulSoup(rsp.text, "html.parser")

        for item in soup.select(".newsItem"):
            youtube_tag = item.select_one("a.youtube").attrs["data-video-id"]
            slug = (
                item.select_one("a.youtube").attrs["data-href"].split("/")[-1]
            )

            url = f"https://youtu.be/{youtube_tag}"

            title = item.select_one("h3").text.strip()
            company = item.select_one(".titelSpan").text.strip()
            company = company.replace(" / ", " ")  # Handle La Monaie De Munt

            config = self.generate_config(slug, company)
            manager.add_job(YtdlpJob(url, f"{title} - {company}", **config))

    def generate_config(
        self: "OperaVisionFactory",
        slug: str,
        company: str,
    ) -> dict:
        """Return yt-dlp configuration for a video."""
        return {
            "allsubtitles": True,
            "extract_flat": "discard_in_playlist",
            "fragment_retries": 10,
            "ignoreerrors": "only_download",
            "outtmpl": {
                "default": f"{self.plugin_id}/{company}/{slug}.%(ext)s",
            },
            "postprocessors": [
                {
                    "key": "FFmpegConcat",
                    "only_multi_video": True,
                    "when": "playlist",
                },
            ],
            "restrictfilenames": True,
            "retries": 10,
            "writesubtitles": True,
        }
