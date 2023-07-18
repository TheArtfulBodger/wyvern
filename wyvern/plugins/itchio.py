"""
Itch.io Downloader.

Download your library from itch.io.
"""

import logging
import re
from contextlib import suppress
from datetime import datetime
from hashlib import md5
from pathlib import Path
from queue import Queue

import requests
import yaml

from wyvern.abstract import Artisan, Factory, Job, Manager

url_regex = re.compile(r"https://(.+)\.itch\.io/(.+)")


class ItchioFactory(Factory):
    """Factory to load itch.io games."""

    plugin_id = "itchio"

    def __init__(self: "ItchioFactory") -> None:
        """Create Object."""

    def load_jobs(self: "ItchioFactory", manager: Manager) -> None:
        """
        Load Games.

        #. Get games from cache
        #. Add Job to queue for each game in cache.
        """
        job = GetGameCacheJob()
        job.do_download(manager)

        for games in job.cache.values():
            for data in games.values():
                manager.add_job(ItchioGameFactoryJob(data))


class ItchioArtisan(Artisan):
    """Download a singular game from itch.io."""

    plugin_id = "itchio"

    def request_job(
        self: "ItchioArtisan",
        manager: Manager,
        job_str: str,
    ) -> Job | None:
        """
        Download a single Game.

        #. Check if game is

                * In the cache (Updating if necessary)
                * A free game

        #. Throw Error if it is neither
        #. return Job
        """
        job = GetGameCacheJob()
        job.do_download(manager)

        # Check if game is in the cache
        publisher, slug = url_regex.match(job_str).groups()
        if publisher in job.cache and slug in job.cache[publisher]:
            return ItchioGameFactoryJob(job.cache[publisher][slug])

        # Now try and see if it is a free game
        try:
            rsp = requests.get(
                f"https://{publisher}.itch.io/{slug}/data.json",
                timeout=10,
            )
            game_id = rsp.json()["id"]

            rsp = requests.get(
                f"https://api.itch.io/games/{game_id}",
                headers={"Authorization": manager.secrets["API_KEY"]},
                timeout=10,
            )
            return ItchioGameFactoryJob(rsp.json())
        except requests.exceptions.Timeout:
            logging.exception("Timeout when Loading URL")
            return None

        # It's neither
        logging.error("Cannot find game: %s", job_str)
        return None


class ItchioGameDownloadableJob(Job):
    """Job for downloading a single downloadable."""

    def __init__(
        self: "ItchioGameFactoryJob",
        upload: dict,
        game: "ItchioGameFactoryJob",
        uuid: str,
    ) -> None:
        """Create Object."""
        self.name = upload["filename"]
        self.data = upload
        self.out_dir = game.out_dir
        self.uuid = uuid
        self.game = game

    def do_download(self: "ItchioGameFactoryJob", manager: Manager) -> None:
        """Download a single file from itch.io."""
        # Check if previous files exist

        yaml_file = (
            Path(manager.plugin_id)
            / self.out_dir
            / ".itch"
            / str(self.data["id"])
        ).with_suffix(".yaml")

        if yaml_file.exists():
            with yaml_file.open() as f:
                data = yaml.safe_load(f)

            old_dt = datetime.fromisoformat(data["updated_at"])

            # Move old file
            old_file = Path(manager.plugin_id) / self.out_dir / data["filename"]

            if data["filename"].exists():
                renamed_file = (
                    old_file.parent
                    / ".old"
                    / (
                        old_file.stem
                        + old_dt.strftime("%Y-%m-%dT%H-%M-%S ")
                        + "."
                        + old_file.extension()
                    )
                )
                renamed_file.parent.mkdir(exist_ok=True, parents=True)
                self.status = f"Moving old file to {renamed_file}"
                self.updated.set()
                old_file.rename(renamed_file)

        # Download File
        self.status = "Downloading File."
        self.updated.set()
        try:
            rsp = requests.get(
                f"https://api.itch.io/uploads/{self.data['id']}/download",
                params=(
                    {"uuid": self.uuid, "api_key": manager.secrets["API_KEY"]}
                    | (
                        {"download_key_id": self.game.id}
                        if self.game.id
                        else {}
                    )
                ),
                stream=True,
                timeout=10,
            )
        except requests.exceptions.Timeout:
            logging.exception("Timeout when Loading URL")
            return

        # Change filename if necessary
        cd = rsp.headers.get("Content-Disposition")
        filename_re = re.search(r'filename="(.+)"', cd)
        if filename_re is not None:
            self.data["filename"], *_ = filename_re.groups(1)

        new_file = (
            Path(manager.plugin_id) / self.out_dir / self.data["filename"]
        )

        # md5 is insecure, but it's what itch uses
        checksum = md5()  # noqa: S324
        with new_file.open("wb") as f:
            for chunk in rsp.iter_content(10240):
                f.write(chunk)
                self.progress = f.tell() / self.data["size"]
                self.updated.set()
                checksum.update(chunk)

        # Check MD5
        if (
            "md5_hash" in self.data
            and checksum.hexdigest() != self.data["md5_hash"]
        ):
            logging.error(
                "Checksum failed for %s. Got: %s, expected %s",
                new_file,
                checksum.hexdigest(),
                self.data["md5_hash"],
            )
            new_file.unlink()
            # Set Error
            return

        # Write YAML File
        yaml_file.parent.mkdir(parents=True, exist_ok=True)
        with yaml_file.open("w") as f:
            yaml.safe_dump(self.data, f)

    def should_skip(self: "ItchioGameFactoryJob", manager: Manager) -> bool:
        """
        See if a job should be skipped.

        Use ``updated_at`` property to see if file donwloaded is out of date.
        """
        if self.data["storage"] != "hosted":
            logging.debug("Skipping because download is not a hosted file.")
            return True
        file = (
            Path(manager.plugin_id)
            / self.out_dir
            / ".itch"
            / str(self.data["id"])
        ).with_suffix(".yaml")
        try:
            with file.open() as f:
                data = yaml.safe_load(f)

            old_dt = datetime.fromisoformat(data["updated_at"])
            new_dt = datetime.fromisoformat(self.data["updated_at"])

            return old_dt >= new_dt  # noqa: TRY300

        except (FileNotFoundError, KeyError, yaml.YAMLError):
            return False


class ItchioGameFactoryJob(Job):
    """Job to download itch.io game."""

    def __init__(self: "ItchioGameFactoryJob", game: dict) -> None:
        """Create Object."""
        self.name = game["game"]["title"]

        self.id = game["id"] if "game_id" in game else None
        self.game_id = (
            game["game_id"] if "game_id" in game else game["game"]["id"]
        )
        self.game_data = game

        self.publisher, self.slug = url_regex.match(
            game["game"]["url"],
        ).groups()
        self.out_dir = f"{self.publisher}/{self.slug}/"

        self.sub_jobs = Queue()

    def do_download(self: "ItchioGameFactoryJob", manager: Manager) -> None:
        """
        Load in downloadable files for game.

        #. Get Uploads
        #. Get UUID for downloading
        #. Add downloadable files to queue
        #. Write YAML as cache
        """
        self.status = "Querying game to get list of Downloadables"

        try:
            rsp = requests.get(
                f"https://api.itch.io/games/{self.game_id}/uploads",
                params={"download_key_id": self.id} if self.id else None,
                headers={"Authorization": manager.secrets["API_KEY"]},
                timeout=10,
            )
        except requests.exceptions.Timeout:
            logging.exception("Timeout when Loading URL")
            return

        uploads = rsp.json()["uploads"]
        self.game_data["uploads"] = [u["id"] for u in uploads]

        try:
            rsp = requests.post(
                "https://api.itch.io/games/46774/download-sessions",
                headers={"Authorization": manager.secrets["API_KEY"]},
                timeout=10,
            )
        except requests.exceptions.Timeout:
            logging.exception("Timeout when Loading URL")
            return

        uuid = rsp.json()["uuid"]

        for u in uploads:
            self.sub_jobs.put(ItchioGameDownloadableJob(u, self, uuid))

        path = Path(manager.plugin_id) / self.out_dir / ".itch/index.yaml"
        path.parent.mkdir(exist_ok=True, parents=True)
        with path.open("w") as f:
            yaml.safe_dump(self.game_data, f)

    def should_skip(self: "ItchioGameFactoryJob", _: Manager) -> bool:
        """
        See if a job should be skipped.

        :warning: As the ``updated_at`` property does not reflect when the game
                  (or it's downloads) was updated, we cannot skip this API call.
                  Otherwise we could see if the file Download cache already
                  exists and is up-to-date.

        Return False, We always have to process this.
        """
        return False


class GetGameCacheFactory(Factory):
    """Simple Factory to create a GetGameCache Job."""

    plugin_id = "itchio"

    def __init__(self: "GetGameCacheFactory") -> None:
        """Create Object."""

    def load_jobs(self: Factory, manager: Manager) -> None:
        """Add a GetGameCacheJob."""
        manager.add_job(GetGameCacheJob())


class GetGameCacheJob(Job):
    """Job to get the games from an itchio account."""

    def __init__(self: "GetGameCacheJob") -> None:
        """Create Object."""
        self.name = "Itch.io Game Cache"
        self.cache = {}

    def should_skip(self: "GetGameCacheJob", _: Manager) -> bool:
        """Will always Try to Download it."""
        return False

    def do_download(self: "GetGameCacheJob", manager: Manager) -> None:
        """
        Update the library cache.

        Will follow the following steps:

        #. Load in existing cache (if it exists).
        #. While there are pages to load

            #. GET request https://api.itch.io/profile/owned-keys?page=i
            #. For every key returned, see if it already exists in cache, adding
               it if it isn't. Exiting the loop if it is.

        #. Write updated cache to file (if specified) or return otherwise.

        As the itch library is ordered in the order items were acquired, we can
        break out of the loop when we hit something already cached.
        """
        # Load in existing cache
        if manager.configuration["CACHE_FILE"] != "":
            path = Path(manager.configuration["CACHE_FILE"])
            with suppress(FileNotFoundError), path.open() as f:
                self.cache = yaml.safe_load(f)
            if self.cache is None:
                self.cache = {}

        # While there are pages to load
        i = 1
        while self._iterate_page(manager, i):
            i += 1

        # Write updated cache to file (if specified) or return otherwise.
        if manager.configuration["CACHE_FILE"] is not None:
            with path.open("w") as f:
                yaml.safe_dump(self.cache, f)

    def _iterate_page(
        self: "GetGameCacheJob",
        manager: Manager,
        i: int,
    ) -> bool:
        uri = "https://api.itch.io/profile/owned-keys"
        self.status = f"Downloading page {i}"
        self.updated.set()
        logging.info("Downloading page %d", i)
        try:
            rsp = requests.get(
                uri,
                timeout=10,
                params={"page": i},
                headers={"Authorization": manager.secrets["API_KEY"]},
            )
        except requests.exceptions.Timeout:
            logging.exception("Timeout when Loading URL")
            return False

        j = rsp.json()
        # Validate keys are present

        for key in j["owned_keys"]:
            publisher, slug = url_regex.match(key["game"]["url"]).groups()
            if publisher not in self.cache:
                self.cache[publisher] = {}
            if slug in self.cache[publisher]:
                # As the itch library is ordered in the order items were
                # acquired, we can break out of the loop when we hit
                # something already cached. However, as it is possible to
                # get the same game from multiple bundles, it is worth checking
                # if the created_at dates (when it was added to the library)
                # match.
                if (
                    key["created_at"]
                    == self.cache[publisher][slug]["created_at"]
                ):
                    return False
                continue
            self.cache[publisher][slug] = key

        return len(j["owned_keys"]) != 0
