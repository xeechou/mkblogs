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
import operator

from mkdocs.build_pages import *

log = logging.getLogger('mkdocs')
omit_path = ['index.md', 'img']


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



class ScanContext:
    def __init__(self, config, dir_path):
        """same for all blogs"""
        self.site_navigation = nav.SiteNavigation(config['pages'], config['use_directory_urls'])
        loader = jinja2.FileSystemLoader(config['theme_dir'])
        self.env = jinja2.Environment(loader=loader)
        """end: same for all blogs"""
        """
        since all files in the same dir all share the have same reference to
        media files, we just use a dummpy path to handle it.
        """
        dummpy = os.path.join(dir_path, 'dummpy')
        dummpy_page = nav.Page(None, url=utils.get_blog_url_path(dummpy),
                path=dummpy, url_context=nav.URLContext())

        site_navigation.update_path(dummpy_page)
        self.global_context = get_global_context(self.site_navigation, config)


def _build_blog(input_path, output_path, config, scan_context):
    """
    convert a blog from @input_path to @output_path html, this func differ from
    _build_page where it use a page struct.
    """
    try:
        input_content = open(input_path, 'r').read()
    except IOError:
        log.error('file not found: %s', input_path)
        return

    if PY2:
        input_content = input_content.decode('utf-8')

    # Process the markdown text

    #TODO: we need a different convert_markdown coz:
    #1. convert_markdown gives wrong links.
    #2. we need a title here.
    html_content, toc, meta = convert_markdown(
        input_content, #without site_navigation
        extensions=config['markdown_extensions'], strict=config['strict']
    )

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

def read_ignore(ignored_file):
    ignored_list = []
    if not os.path.isfile(ignored_file):
        pass
    else:
        with open(ignored_file) as f:
            for line in f:
                ignored_files.append(line)
            f.close()
    return ignored_list

def add_top_n(newest_paths, to_add, n):
    to_sort = newest_paths.extend(to_add)
    if not to_sort:
        return []
    return sorted(to_sort, key=operator.itemgetter(1), \
            reverse=True)[:n]

def write_indexmd(fp, files_path):
    #TODO
    pass

def recursive_scan(this_dir, config, n_new, cata_list, genindex=True):
    """
    @this_dir starts inside docs, so you will never see 'docs/' in it. Inside
    function, we use true_path to represent the relpath from '/' to now
    
    also, we record the newest N blogs
    """
    """
    we use one single global_context to represent all files in the same dir
    """
    scan_context = ScanContext(config, this_dir)
    global_context = scan_context.get_global_context(dummpy_page, config)

    global omit_path   #TODO: fix this
    newest_paths = []
    local_paths = {}
    dot_ignore = '.ignore'
    
    docs_dir = os.path.join(config['docs_dir'], this_dir)
    htmls_dir = os.path.join(config['site_dir'], this_dir)

    paths = os.listdir(docs_dir)
    ignored_files = read_ignore(os.path.join(docs_dir, dot_ignore))
    for f in paths:
        doc_path  = os.path.join(docs_dir,  f)
        html_path = utils.get_blog_html_path(os.path.join(htmls_dir, f))

        #locally ignored
        if f == dot_ignore:
            continue
        if f in ignored_files:
            continue
        #globally ignored,
        if doc_path in omit_path:
            continue

        if utils.is_markdown_file(doc_path):
            addtime = os.path.getatime(doc_path)
            local_paths[f] = addtime
            newest_paths.append((doc_path, addtime))
#XXX: build every page
            _build_blog(doc_path, html_path, config, scan_context)   

        elif os.path.isdir(doc_path):
            sub_newest_paths = recursive_scan(os.path.join(this_dir, f), config, n_new,
                    cata_list, scan_context)
#XXX: update top N pages
            add_top_n(newest_paths, sub_newest_paths, n_new)
        else:
            continue

        #now, we should generate a index.md for this dir
    if genindex == True:
        index_path = os.path.join(docs_dir, 'index.md')
        index_md = open(index_path, 'w')
        write_indexmd(index_md, local_paths)
        index_md.close()
        _build_blog(index_path, utils.get_blog_html_path(index_path), config,
                scan_context)
#XXX: add to cata_list
        cata_list.append(this_dir)

    #XXX: restore context
    return newest_paths



def build_blogs(config):
    build_path = config['docs_dir']
    topn = config.get('n_blogs_to_show') or 5

    scan_context = ScanContext(config)
    
    cata_list = []
    n_newest_path = newest_blogs = recursive_scan('.', config, 
            n_pages, cata_list,genindex=False)
    #write index.md and cata.md

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
    print(config['pages'])
    scan_context = Build.ScanContext(config)
    #so basically you need add a '/' to urls, 

    cata_list = []
    news_path = recursive_scan('.', config, 5, cata_list, scan_context, genindex=False)

    #scan_context.set_global_context(nav.Page(None,url='/test/test.md', path='test/test.md',\
    #    url_context=nav.URLContext), config)
    #content = Build._build_blog('tests/test.md', config, scan_context)
    #print(content)
