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




def get_global_context(page, nav, config):
    """
    for blogs, url_context here usually config['docs'], because we need to
    locate the resource files, later. When we compile blogs, remove
    config['docs'] information as we only want relative urls inside config['docs']
    """
    site_name = config['site_name']

    if config['site_favicon']:
        site_favicon = page.url_context.make_relative('/' + config['site_favicon'])
    else:
        site_favicon = None

    page_description = config['site_description']

    extra_javascript = utils.create_media_urls(url_context=page.url_context, url_list=config['extra_javascript'])

    extra_css = utils.create_media_urls(url_context=page.url_context, url_list=config['extra_css'])
    base_url = page.url_context.make_relative('/')

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
        'base_url': base_url, #base_url is a relative_url from page to themes
        'homepage_url': base_url + nav.homepage.abs_url,

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

def build_catalog(page, config, site_navigation, env):
    """
    write the top catalog page for blogs according to catalist.
    """
    catalist = config['catalist']
    input_path = page.input_path
    with open(input_path, 'w') as f:
        for key in catalist.keys():
            f.write(add_category(key))
            for (blog_name, blog_path) in catalist[key]:
                """hard code the blog addr to its html addr, fix this later"""
                blog_url = os.path.join(config['site_dir'], 
                        utils.get_html_path(blog_path))
                f.write(add_cate_blog(blog_name, blog_url))
        f.close()
    _build_page(page, config, site_navigation, env)


#XXX:fixed
def build_404(config, env, site_navigation):

    log.debug("Building 404.html page")

    try:
        template = env.get_template('404.html')
    except TemplateNotFound:
        return
    page = nav.Page('Page Not Found', '404.html', '404.md')
    global_context = get_global_context(page, site_navigation, config)

    output_content = template.render(global_context)
    utils.write_file(output_content.encode('utf-8'), '404.html')

def get_blog_meta(data):
    #TODO: either we change the template or blog_record file format
    blog = {}
    blog['title'] = data[0]
    blog['date'] = data[1]
    blog['tags'] = data[2]
    return blog

def build_index(page, config, site_navigation, env):
    """
    the blogs_on_index is a list of name of blogs, under docs/
    """
    dot_record = config.get('dot_record') or '.record'
    blog_record = utils.load_json(os.path.join(config['docs_dir'],dot_record))

    template = env.get_template('base.html')

    context = get_global_context(page, site_navigation, config)
    context.update({'structure' : 'ind.html'})
    topblogs = []

    newblogs = config['blogs_on_index']
    for blog_path in newblogs:
        try:
            input_content = open(os.path.join(config['docs_dir'], blog_path),'r').read()
        except:
            log.error('failed to generate index from %s', blog_path)
            continue
        if PY2:
            input_content = input_content.decode('utf-8')

        newblog = nav.Blog(utils.get_url_path(blog_path), blog_path)
        prefix=os.path.join(config['site_dir'], os.path.dirname(blog_path))
        html_content, table_of_contents, meta = parser.convert_markdown(
            input_content, newblog,
            extensions=config['markdown_extensions'],
            strict=config['strict'],
            prefix=prefix)

        blog_meta = get_blog_meta(blog_record[blog_path])
        blog_meta['content'] = html_content
        topblogs.append(blog_meta)
        #get their attributes
    context['topblogs'] = topblogs

    output_content = template.render(context)
    utils.write_file(output_content.encode('utf-8'), 'index.html')

#XXX:fixed
def _build_page(page, config, site_navigation, env):
    # Read the input file
    input_path = page.input_path
    output_path = page.output_path

    try:
        input_content = open(input_path, 'r').read()
    except IOError:
        log.error('file not found: %s', input_path)
        return

    if PY2:
        input_content = input_content.decode('utf-8')

    # Process the markdown text
    html_content, table_of_contents, meta = parser.convert_markdown(
        input_content, page,
        extensions=config['markdown_extensions'], strict=config['strict']
    )

    context = get_global_context(page, site_navigation, config)
    context.update(get_page_context(
        page, html_content, table_of_contents, meta, config
    ))

    # Allow 'template:' override in md source files.
    if 'template' in meta:
        template = env.get_template(meta['template'][0])
    else:
        template = env.get_template('base.html')

    # Render the template.
    output_content = template.render(context)

    # Write the output file.
    utils.write_file(output_content.encode('utf-8'), output_path)

#XXX:fixed
def build_pages(config, site_navigation):
    """
    Builds all the pages and writes them into the build directory.
    """
    #site_navigation = nav.SiteNavigation(config['pages'])
    loader = jinja2.FileSystemLoader(config['templates_dir'])
    env = jinja2.Environment(loader=loader)

    index = site_navigation.get_page('Home')
    index.set_builder(build_index)
    catalist = site_navigation.get_page('Catalogs')
    catalist.set_builder(build_catalog)
    build_404(config, env, site_navigation)

    for page in site_navigation.walk_pages():
        try:
            log.debug("Building page %s", page.input_path)
            build_page = page.get_builder() or _build_page
            build_page(page, config, site_navigation, env)
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
