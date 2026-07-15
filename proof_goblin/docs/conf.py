"""Sphinx configuration for the Proof Goblin documentation."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as distribution_version

project = "Proof Goblin"
author = "We Build Reactions"
copyright = "2025, We Build Reactions"

try:
    release = distribution_version("proof-goblin")
except PackageNotFoundError:
    release = "0.1.0"
version = ".".join(release.split(".")[:2])

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

source_suffix = {
    ".md": "markdown",
}
root_doc = "index"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

myst_enable_extensions = [
    "colon_fence",
    "deflist",
]
myst_heading_anchors = 3

html_theme = "furo"
html_title = f"{project} {release}"
html_static_path = ["_static"]
