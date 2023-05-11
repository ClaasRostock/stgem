# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'stgem'
copyright = '2022, ÅAU'
author = 'ÅAU'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'myst_parser',
    'sphinx.ext.napoleon',
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
]

# Napoleon settings
napoleon_numpy_docstring = False

# Define file suffixes to include
source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

root_doc = "docs/source/index"

templates_path = ['_templates']
exclude_patterns = ['venv', 'output', 'problems', 'tests', 'tests-matlab']

import commonmark

def docstring(app, what, name, obj, options, lines):
    md = "\n".join(lines)
    ast = commonmark.Parser().parse(md)
    rst = commonmark.ReStructuredTextRenderer().render(ast)

    lines.clear()
    lines += _normalize_docstring_lines(rst.splitlines())

def _normalize_docstring_lines(lines: list[str]) -> list[str]:
    is_param_field = False

    new_lines = []
    for l in lines:
        if l.lstrip().startswith(":param"):
            is_param_field = True
        elif is_param_field:
            if not l.strip():  # Blank line reset param
                is_param_field = False
            else:  # Restore indentation
                l = f"    {l.lstrip()}"
        new_lines.append(l)
    return new_lines

def setup(app):
    app.connect("autodoc-process-docstring", docstring)

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
