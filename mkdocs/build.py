# coding: utf-8
from __future__ import print_function

from datetime import datetime

from jinja2.exceptions import TemplateNotFound
import mkdocs

from mkdocs import nav, toc, utils
from mkdocs.compat import urljoin, PY2
from mkdocs.relative_path_ext import RelativePathExtension
import jinja2
import json
import markdown
import os
import logging

from mkdocs.build_pages import *

log = logging.getLogger('mkdocs')

class ScanContext:
    def __init__(self, config):
        self.site_navigation = nav.SiteNavigation(config['pages'], config['use_directory_urls'])
        loader = jinja2.FileSystemLoader(config['theme_dir'])
        self.env = jinja2.Environment(loader=loader)

        self.global_context = get_global_context(self.site_navigation, config)

BLANK_BLOG_CONTEXT = {
        'page_title': None,
        'page_description': None,

        'content': None,
        'toc': None,
        'meta': None,


        'canonical_url': None,

        'current_page': None, #maybe I should use home?
        'previous_page': None,
        'next_page': None
        }

def get_blog_context(config, title, html, toc, meta):
    """
    update a blogs' page context
    """
    return {
            'page_title': title,
            #no description for a blog

            #there is no next page and previous page for blo
            'content' : html,
            'toc' : toc,
            'meta' : meta
            }
#XXX: we cannot reuse _build_page function without a huge surgery, it is tiled
#with a page object, but in our context, we don't know our title in advance.
#TODO
def _build_blog(path, config, scan_context):
    try:
        input_content = open(path, 'r').read()
    except IOError:
        log.error('file not found: %s', input_path)
        return

    if PY2:
        input_content = input_content.decode('utf-8')

    # Process the markdown text
    html_content, toc, meta = convert_markdown(
        input_content, #without site_navigation
        extensions=config['markdown_extensions'], strict=config['strict']
    )
    #TODO:resolve links here

    #TODO:render pages, TODO: get_blog_context, blank_blog_context
    context = scan_context.global_context
    context.update(BLANK_BLOG_CONTEXT)
    context.update(get_blog_context(config, None, html_content, toc, meta))

    # Allow 'template:' override in md source files.
    if 'template' in meta:
        template = scan_context.env.get_template(meta['template'][0])
    else:
        template = scan_context.env.get_template('base.html')

    # Render the template.
    return template.render(context)


def recursive_scan(this_path, config, n_new, cata_list, scan_context, genindex=True):
    """
    Every directory is a catalog, if we find one, we will append dir name to
    cata_list, and build a index.html for it.

    also, we record the newest N blogs
    """
    global omit_path    #TODO: fix this
    newest_paths = []
    local_paths = {}
    abs_paths = {}

    paths = os.listdir(this_path)
    ignored_files = read_ignore(os.path.join(this_path, dot_ignore))
    for f in paths:
        #locally ignored
        if f == dot_ignore:
            continue
        if f in ignored_files:
            continue
        #globally ignored,
        abs_path = os.path.join(this_path, f)
        if abs_path in omit_path:
            continue

        #XXX: @abs_path is not abs path at all, it starts at 'docs'
        if os.path.isfile(abs_path):
            addtime = os.path.getatime(abs_path)
            local_paths[f] = addtime
            build_
            newest_paths.append((abs_path, addtime))
#XXX: build every page
            _build_blog(abs_path, config, scan_context)   

        elif os.path.isdir(abs_path):
            sub_newest_paths = recursive_scan(abs_path)
#XXX: update top N pages
            add_top_n(newest_paths, sub_newest_paths)
        else:
            continue

        #now, we should generate a index.md for this dir
    if genindex == True:
        index_md = open(os.path.json(parent_path, 'index.md'), 'w')
        write_indexmd(index_md, local_paths)
        index_md.close()
#XXX: add to cata_list
        #XXX, build page for index.md
        cata_list.append(this_path) 

    return newest_path


def build_blogs(config):
    build_path = config['docs_dir']
    topn = config.get('n_blogs_to_show') or 5

    scan_context = ScanContext(config)
    
    cata_list = []
    n_newest_path = newest_blogs = recursive_scan(build_path, config, 
            n_pages, cata_list,genindex=False)

def build(config, live_server=False, dump_json=False, clean_site_dir=False):
    """
    Perform a full site build.
    """
    if clean_site_dir:
        print("Cleaning site directory")
        utils.clean_directory(config['site_dir'])
    if not live_server:
        print("Building documentation to directory: %s" % config['site_dir'])
        if not clean_site_dir and site_directory_contains_stale_files(config['site_dir']):
            print("Directory %s contains stale files. Use --clean to remove them." % config['site_dir'])

    #we ignore dump json
    if dump_json:
        build_pages(config, dump_json=True)
        return

    # Reversed as we want to take the media files from the builtin theme
    # and then from the custom theme_dir so the custom versions take take
    # precedence.
    for theme_dir in reversed(config['theme_dir']):
        log.debug("Copying static assets from theme: %s", theme_dir)
        utils.copy_media_files(theme_dir, config['site_dir'])

    log.debug("Copying static assets from the docs dir.")
    utils.copy_media_files(config['docs_dir'], config['site_dir'])

    log.debug("Building markdown pages.")
    build_pages(config)
    build_blogs(config)

import config as Config
import build as Build
from lxml import html

if __name__ == "__main__":
    config = Config.load_config('tests/test_conf.yml')
    scan_context = Build.ScanContext(config)
    #page link problem need to be resolved
    content = Build._build_blog('tests/test.md', config, scan_context)
    print (content)
