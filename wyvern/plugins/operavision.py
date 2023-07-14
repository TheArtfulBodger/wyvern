"""
Operavision Factory and Job.

Download All Videos and Credits for Performances on operavision.eu
"""

import logging
from pathlib import Path
from xml.dom.minidom import getDOMImplementation

import requests
from bs4 import BeautifulSoup

from wyvern.abstract import Factory, Job, Manager
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
            manager.add_job(OperaVisionNFOJob(title, company, slug))

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


class OperaVisionNFOJob(Job):
    """Job to create an NFO file from a performance page."""

    def __init__(
        self: "OperaVisionNFOJob",
        name: str,
        company: str,
        slug: str,
    ) -> "OperaVisionNFOJob":
        """Create the job."""
        self.name = name
        self.output_file = (
            Path(OperaVisionFactory.plugin_id) / company / slug
        ).with_suffix(".nfo")
        self.slug = slug

    def do_download(self: "OperaVisionNFOJob", _: Manager) -> None:
        """
        Do The Download.

        Scrapes the content from the performance page.
        """
        uri = f"https://operavision.eu/performance/{self.slug}"
        try:
            rsp = requests.get(
                uri,
                timeout=10,
            )
        except requests.exceptions.Timeout:
            logging.exception("Timeout when Loading URL")
        soup = BeautifulSoup(rsp.text, "html.parser")

        doc = getDOMImplementation().createDocument(None, "video", None)
        video = doc.documentElement

        e = doc.createElement("uniqueid")
        e.attributes["type"] = "ovdl"
        e.appendChild(doc.createTextNode(uri))
        video.appendChild(e)

        e = doc.createElement("title")
        e.appendChild(doc.createTextNode(self.name))
        video.appendChild(e)

        e = doc.createElement("outline")
        e.appendChild(
            doc.createTextNode(soup.select("p.intro")[0].text.strip()),
        )
        video.appendChild(e)

        e = doc.createElement("plot")
        plot = soup.select(":has(> p.intro) p:not(.intro)")
        plot = "\n\n".join([s.text.strip() for s in plot])
        e.appendChild(doc.createTextNode(plot.strip()))
        video.appendChild(e)

        name_str = ""
        role_str = ""
        for actor in soup.select(".castTable .castRow"):
            e = doc.createElement("actor")
            children = [
                "".join([c for c in i.text.strip() if c.isprintable()])
                for i in actor.children
            ]
            if len(set(children)) == 1:
                continue
            if children[1] != "":
                name_str = children[1]
            if children[0] != "":
                role_str = children[0]
            name = doc.createElement("name")
            name.appendChild(doc.createTextNode(name_str))
            role = doc.createElement("role")
            role.appendChild(doc.createTextNode(role_str))
            e.appendChild(name)
            e.appendChild(role)
            video.appendChild(e)

        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        with self.output_file.open("w") as f:
            doc.writexml(
                f,
                addindent="    ",
                newl="\n",
            )

    def should_skip(self: "OperaVisionNFOJob", _: Manager) -> bool:
        """Determine if job can be skipped."""
        return self.output_file.exists()
