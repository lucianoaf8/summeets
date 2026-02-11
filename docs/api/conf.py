"""Sphinx configuration for Summeets API documentation."""

import os
import sys

# Add project root to path for autodoc
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

project = "Summeets"
copyright = "2025, Summeets Contributors"
author = "Summeets Contributors"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx_autodoc_typehints",
]

# Napoleon settings (Google/NumPy docstring styles)
napoleon_google_docstrings = True
napoleon_numpy_docstrings = False

# Autodoc settings
autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
}
autodoc_member_order = "bysource"

# Type hints
always_document_param_types = True
typehints_defaults = "comma"

# Intersphinx mapping
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "pydantic": ("https://docs.pydantic.dev/latest/", None),
}

# HTML output
html_theme = "alabaster"
html_static_path = []

# Exclude patterns
exclude_patterns = ["_build"]
