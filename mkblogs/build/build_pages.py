# coding: utf-8
from __future__ import print_function

from datetime import datetime
from jinja2.exceptions import TemplateNotFound

import mkblogs
from mkblogs import toc, utils
from mkblogs.compat import urljoin, PY2
from mkblogs.build import html as parser
from mkblogs.build import nav
import jinja2
import json
import markdown
import os
import logging
import posixpath

log = logging.getLogger('mkblogs')




def get_global_context(nav, config):
    """
    Given the SiteNavigation and config, generate the context which is relevant
    to app pages.
    """

    site_name = config['site_name']

    if config['site_favicon']:
        site_favicon = nav.url_context.make_relative('/' + config['site_favicon'])
    else:
        site_favicon = None

    page_description = config['site_description']

    extra_javascript = utils.create_media_urls(nav=nav, url_list=config['extra_javascript'])

    extra_css = utils.create_media_urls(nav=nav, url_list=config['extra_css'])

    #print(nav.url_context.base_path)
    #print (posixpath.relpath('/', start=nav.url_context.base_path))

    return {
        'site_name': site_name,
        'site_author': config['site_author'],
        'favicon': site_favicon,
        'page_description': page_description,

        # Note that there's intentionally repetition here. Rather than simply
        # provide the config dictionary we instead pass everything explicitly.
        #
        # This helps ensure that we can throughly document the context that
        # gets passed to themes.
        'repo_url': config['repo_url'],
        'repo_name': config['repo_name'],
        'nav': nav,
        'base_url': nav.url_context.make_relative('/'), #base_url is a
                                                        #relative_url from page to themes
        'homepage_url': nav.homepage.url,
        #print(homepage_url)

        'extra_css': extra_css,
        'extra_javascript': extra_javascript,

        'include_nav': config['include_nav'],
        'include_next_prev': config['include_next_prev'],
        'include_search': config['include_search'],

        'copyright': config['copyright'],
        'google_analytics': config['google_analytics'],

        'mkblogs_version': mkblogs.__version__,
        'build_date_utc': datetime.utcnow()
    }


def get_page_context(page, content, toc, meta, config):
    """
    Generate the page context by extending the global context and adding page
    specific variables.
    """

    if page.is_homepage or page.title is None:
        page_title = None
    else:
        page_title = page.title

    if page.is_homepage:
        page_description = config['site_description']
    else:
        page_description = None

    if config['site_url']:
        base = config['site_url']
        if not base.endswith('/'):
            base += '/'
        canonical_url = urljoin(base, page.abs_url.lstrip('/'))
    else:
        canonical_url = None


    return {
        'page_title': page_title,
        'page_description': page_description,

        'content': content,
        #'toc' : toc,
        'toc': None,
        'meta': meta,


        'canonical_url': canonical_url,

        'current_page': page,
        'previous_page': page.previous_page,
        'next_page': page.next_page,
    }

def add_category(key):
    return "### Category-{0}\n".format(key.encode('utf8'))
def add_cate_blog(blog, path):
    return "+ [{0}]({1})\n".format(blog.encode('utf8'), path.encode('utf8'))

def build_catalog(config, catalist):
    """
    write the top catalog page for blogs according to catalist,
    catalist is list of dirnames, in mkblogs's scenario, it will treat dirname as
    actual file, and transfer to 'dirname/index.md', which points to exact
    location of the index file. If using our senario, we will treat it as dir,
    then it points to dirname.
    """
    cata_path = config['pages'][1][0]
    path = os.path.join(cata_path)
    with open(path, 'w') as f:
        for key in catalist.keys():
            f.write( add_category(key))
            for (blog_name, blog_path) in catalist[key]:
                blog_path = os.path.join(config['docs_dir'],blog_path)
                f.write( add_cate_blog(blog_name, blog_path))
        f.close()

def build_index(config, newblogs):
    """simply generate a list of blogs for template to render, but we need to
    make html and """
    for blog in newblogs:
        pass

def build_404(config, env, site_navigation):

    log.debug("Building 404.html page")

    try:
        template = env.get_template('404.html')
    except TemplateNotFound:
        return

    global_context = get_global_context(site_navigation, config)

    output_content = template.render(global_context)
    output_path = os.path.join(config['docs_dir'], '404.html')
    utils.write_file(output_content.encode('utf-8'), output_path)


def _build_page(page, config, site_navigation, env):

    # Read the input file
    input_path = os.path.join(config['docs_dir'], page.input_path)

    try:
        input_content = open(input_path, 'r').read()
    except IOError:
        log.error('file not found: %s', input_path)
        return

    if PY2:
        input_content = input_content.decode('utf-8')

    # Process the markdown text
    html_content, table_of_contents, meta = parser.convert_markdown(
        input_content, site_navigation,
        extensions=config['markdown_extensions'], strict=config['strict']
    )

    context = get_global_context(site_navigation, config)
    context.update(get_page_context(
        page, html_content, table_of_contents, meta, config
    ))

    # Allow 'template:' override in md source files.
    if 'template' in meta:
        template = env.get_template(meta['template'][0])
    elif site_navigation.page_template(page):
        template = env.get_template(site_navigation.page_template(page))
    else:
        template = env.get_template('base.html')

    # Render the template.
    output_content = template.render(context)

    # Write the output file.
    output_path = os.path.join(config['docs_dir'], page.output_path)
    utils.write_file(output_content.encode('utf-8'), output_path)


def build_pages(config):
    """
    Builds all the pages and writes them into the build directory.
    """
    site_navigation = nav.SiteNavigation(config['pages'])
    loader = jinja2.FileSystemLoader(config['theme_dir'])
    env = jinja2.Environment(loader=loader)

    #deal with
    index = site_navigation.get_page('index.md')
    index.set_builder(build_index, config['blogs_on_index'])
    catalist = site_navigation.get_page('catalist.md')
    catalist.set_builder(build_catalog, config['catalist'])

    build_404(config, env, site_navigation)

    for page in site_navigation.walk_pages():
        try:
            log.debug("Building page %s", page.input_path)
            if page.has_builder:
                page.func(page.build_data)
            _build_page(page, config, site_navigation, env)
        except:
            log.error("Error building page %s", page.input_path)
            raise




def site_directory_contains_stale_files(site_directory):
    """
    Check if the site directory contains stale files from a previous build.
    Right now the check returns true if the directory is not empty.
    A more sophisticated approach should be found to trigger only if there are
    files that won't be overwritten anyway.
    """
    if os.path.exists(site_directory):
        if os.listdir(site_directory):
            return True
    return False