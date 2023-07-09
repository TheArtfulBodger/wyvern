"""
Yaml Data Store.

Used for storing data in a yaml file.
"""

from contextlib import suppress
from pathlib import Path

import yaml

from wyvern.abstract import DataStore


class YamlDataStore(DataStore):
    """
    Yaml Data Store.

    Used for storing data in a yaml file.
    """

    def __init__(self: "YamlDataStore", plugin_id: str, file: Path) -> None:
        """
        Create a YamlDataStore.

        :param plugin_id: The plugin for the data store.
        :param file: The Path to the YAML file.
        """
        self.plugin_id = plugin_id
        self.file = file

    def __getitem__(self: "YamlDataStore", key: str) -> str:
        """Get the stored value."""
        data = {}
        with suppress(FileNotFoundError), self.file.open() as f:
            data = yaml.safe_load(f)
        if self.plugin_id in data:
            plugin = data[self.plugin_id]
            return plugin.get(key, "")
        return ""

    def __setitem__(self: "YamlDataStore", key: str, value: str) -> None:
        """Store the value."""
        data = {}
        with suppress(FileNotFoundError), self.file.open() as f:
            data = yaml.safe_load(f)
        if self.plugin_id not in data:
            data[self.plugin_id] = {}
        data[self.plugin_id][key] = value
        with self.file.open("w") as f:
            yaml.safe_dump(data, f)
