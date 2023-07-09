"""
Sphinx Configuration File.

Minimal configuration to avoid duplication of names/versions across files.
"""
# ruff: noqa: INP001

import os
import sys

from sphinx_pyproject import SphinxConfig

config = SphinxConfig("../pyproject.toml", globalns=globals())
html_short_title = f"{name} Documentation".title()  # noqa: F821

sys.path.insert(0, os.path.relpath(".."))
extensions = [
    "sphinx.ext.autodoc",  # Core library for html generation from docstrings
    "sphinx.ext.autosummary",  # Create neat summary tables
    "sphinx.ext.todo",  # Format TODOs in docstrings
]
autosummary_generate = True
todo_include_todos = True


templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


html_theme = "piccolo_theme"
html_static_path = ["_static"]
