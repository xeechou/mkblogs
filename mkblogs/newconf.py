# coding: utf-8

from mkblogs import utils
from mkblogs.compat import urlparse
from mkblogs.exceptions import ConfigurationError

import os, sys
import logging
import os

log = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    'site_name': None,
    'pages': None,

    'site_url': None,
    'site_description': None,
    'site_author': None,
    'site_favicon': None,

    'theme': 'mkdocs',
    'docs_dir': 'docs',
    'site_dir': 'site',
    'theme_dir': None,

    'copyright': None,
    'google_analytics': None,

    # The address on which to serve the livereloading docs server.
    'dev_addr': '127.0.0.1:8000',

    # If `True`, use `<page_name>/index.hmtl` style files with hyperlinks to the directory.
    # If `False`, use `<page_name>.html style file with hyperlinks to the file.
    # True generates nicer URLs, but False is useful if browsing the output on a filesystem.
    # This is too annoying
    #'use_directory_urls': True,

    # Specify a link to the project source repo to be included
    # in the documentation pages.
    'repo_url': None,

    # A name to use for the link to the project source repo.
    # Default: If repo_url is unset then None, otherwise
    # "GitHub" or "Bitbucket" for known url or Hostname for unknown urls.
    'repo_name': None,

    # Specify which css or javascript files from the docs
    # directionary should be additionally included in the site.
    # Default: List of all .css and .js files in the docs dir.
    'extra_css': None,
    'extra_javascript': None,

    # Determine if the site should include the nav and next/prev elements.
    # Default: True if the site has more than one page, False otherwise.
    'include_nav': None,
    'include_next_prev': None,

    # PyMarkdown extension names.
    'markdown_extensions': (),

    # Determine if the site should generate a json search index and include
    # search elements in the theme. - TODO
    'include_search': False,

    # Determine if the site should include a 404.html page.
    # TODO: Implment this. Make this None, have it True if a 404.html
    # template exists in the theme or docs dir.
    'include_404': False,

    # enabling strict mode causes MkDocs to stop the build when a problem is
    # encountered rather than display an error.
    'strict': False,

    #insert self defined pages after default pages, test Based on title
    #and another thing to be noticed, here we didn't know anything about
    #'docs_dir', so we decide to ignore it first, and append them later
    'default pages' : [['index.md', 'Home'], ['catalist.md', 'Catalog']]
}

def import_conf(filepath):
    conf = None
    directory, modpath = os.path.split(filepath)
    modname = os.path.splitext(modpath)[0]
    path = list(sys.path)
    sys.path.insert(0, directory)

    #new import the module
    try:
        conf = __import__(modname).__dict__.copy()
        del conf['__builtins__']
    finally:
        sys.path[:] = path

    return conf


def load_config(filename='mkblogs.py', options=None):
    options = options or {}
    if 'config' in options:
        filename = options['config']
    if not os.path.exists(filename):
        raise ConfigurationError("Config file '%s' does not exist." % filename)

    conf = import_conf(filename)
