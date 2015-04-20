# coding: utf-8

from mkblogs import utils
from mkblogs.compat import urlparse
from mkblogs.exceptions import ConfigurationError

import logging
import os
import yaml

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
    'use_directory_urls': True,

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
    'default pages' : [('index.md', 'Home'), ('catalist.md', 'Catalog')]
}

def load_config(filename='mkblogs.yml', options=None):
    options = options or {}
    if 'config' in options:
        filename = options['config']
    if not os.path.exists(filename):
        raise ConfigurationError("Config file '%s' does not exist." % filename)
    with open(filename, 'r') as fp:
        user_config = yaml.load(fp)
        if not isinstance(user_config, dict):
            raise ConfigurationError("The mkblogs.yml file is invalid. See http://www.mkdocs.org/user-guide/configuration/ for more information.")
    user_config.update(options)
    return validate_config(user_config)


def validate_config(user_config):
    config = DEFAULT_CONFIG.copy()

    theme_in_config = 'theme' in user_config

    config.update(user_config)

    if not config['site_name']:
        raise ConfigurationError("Config must contain 'site_name' setting.")

    # Validate that the docs_dir and site_dir don't contain the
    # other as this will lead to copying back and forth on each
    # and eventually make a deep nested mess.
    abs_site_dir = os.path.abspath(config['site_dir'])
    abs_docs_dir = os.path.abspath(config['docs_dir'])
    if abs_docs_dir.startswith(abs_site_dir):
        raise ConfigurationError(
            "The 'docs_dir' can't be within the 'site_dir'.")
    elif abs_site_dir.startswith(abs_docs_dir):
        raise ConfigurationError(
            "The 'site_dir' can't be within the 'docs_dir'.")

    # If not specified, then the 'pages' config simply are catalist and index.md
    pages = config['default pages']

    for page in config['pages']:
        if page[1] == 'Home' and page[0] != 'index.md':
            raise NameError('Invalid home name')
        elif page[1] == 'Catalog':
            pages[1] = (page[0], 'Catalog')
        else:
            pages.append(page)

    extra_css = []
    extra_javascript = []
    for (dirpath, dirnames, filenames) in os.walk(config['docs_dir']):
        for filename in sorted(filenames):
            fullpath = os.path.join(dirpath, filename)
            relpath = os.path.relpath(fullpath, config['docs_dir'])

            if utils.is_css_file(filename):
                extra_css.append(relpath)
            elif utils.is_javascript_file(filename):
                extra_javascript.append(relpath)

    if config['extra_css'] is None:
        config['extra_css'] = extra_css

    if config['extra_javascript'] is None:
        config['extra_javascript'] = extra_javascript

    package_dir = os.path.dirname(__file__)
    theme_dir = [os.path.join(package_dir, 'themes', config['theme'])]

    if config['theme_dir'] is not None:
        # If the user has given us a custom theme but not a
        # builtin theme name then we don't want to merge them.
        if not theme_in_config:
            theme_dir = []
        theme_dir.insert(0, config['theme_dir'])

    config['theme_dir'] = theme_dir

    if config['repo_url'] is not None and config['repo_name'] is None:
        repo_host = urlparse(config['repo_url']).netloc.lower()
        if repo_host == 'github.com':
            config['repo_name'] = 'GitHub'
        elif repo_host == 'bitbucket.org':
            config['repo_name'] = 'Bitbucket'
        else:
            config['repo_name'] = repo_host.split('.')[0].title()

    if config['include_next_prev'] is None:
        config['include_next_prev'] = len(config['pages']) > 1

    if config['include_nav'] is None:
        config['include_nav'] = len(config['pages']) > 1

    # To Do:

    # The docs dir must exist.
    # The theme dir must exist.
    # Ensure 'theme' is one of 'mkblogs', 'readthedocs', 'custom'
    # A homepage 'index' must exist.
    # The theme 'base.html' file must exist.
    # Cannot set repo_name without setting repo_url.
    # Cannot set 'include_next_prev: true' when only one page exists.
    # Cannot set 'include_nav: true' when only one page exists.
    # Error if any config keys provided that are not in the DEFAULT_CONFIG.

    return config
