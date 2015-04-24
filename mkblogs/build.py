# coding: utf-8
from __future__ import print_function

from datetime import datetime

from jinja2.exceptions import TemplateNotFound
import mkblogs

from mkblogs import nav, utils
from mkblogs import html as parser
from mkblogs.compat import urljoin, PY2
from mkblogs.relative_path_ext import RelativePathExtension, TitleExtension
import jinja2
import json
import markdown
import os
import logging
import operator

from mkblogs.build_pages import *

log = logging.getLogger('mkblogs')
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
    def __init__(self, config, dir_path, site_navigation):
        """same for all blogs"""
        self.site_navigation = site_navigation
        loader = jinja2.FileSystemLoader(config['theme_dir'])
        self.env = jinja2.Environment(loader=loader)
        """end: same for all blogs"""

        """
        since all files in the same dir all share the have same reference to
        media files, we just use a dummpy path to handle it.
        """
        dummpy = os.path.join(dir_path, 'dummpy')
        dummpy_page = nav.Page(None, url=utils.get_url_path(dummpy),
                path=dummpy, url_context=nav.URLContext())

        self.site_navigation.update_path(dummpy_page)
        self.global_context = get_global_context(self.site_navigation, config)

def _build_blog(path, config, scan_context):
    """
    convert a blog from @input_path to @output_path html, this func differ from
    _build_page where it use a page struct.
    """
    input_path = os.path.join(config['docs_dir'], path)
    try:
        input_content = open(input_path, 'r').read()
    except IOError:
        log.error('file not found: %s', input_path)
        return

    if PY2:
        input_content = input_content.decode('utf-8')

    # Process the markdown text

    #TODO: we need a different convert_markdown coz:
    #okay, there is a hack here, we pase a externsion struct in, when we
    #return, there will be md struct there. we can get what we want from md.
    extens = config['markdown_extensions']
    extens.append(TitleExtension())

    html_content, toc, meta, md = parser.convert_markdown(
        input_content, #without site_navigation
        extensions=extens, strict=config['strict'], wantmd=True
    )
    title = getattr(md, 'doc_title', '')
    del md

    #if we want to parallize, we have to acquire a lock for global_context
    context = scan_context.global_context
    context.update(BLANK_BLOG_CONTEXT)
    context.update(get_blog_context(config, title, html_content, toc, meta))

    # Allow 'template:' override in md source files.
    if 'template' in meta:
        template = scan_context.env.get_template(meta['template'][0])
    else:
        template = scan_context.env.get_template('base.html')

    # Render the template.
    final_content =  template.render(context)
    #just write right in the directory
    output_path = os.path.splitext(input_path)[0] + '.html'
    with open(output_path, 'w') as f:
        f.write(final_content.encode('utf8'))
        f.close()
    return None #return title

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
    newest_paths.extend(to_add)
    if not newest_paths:
        return []
    return sorted(newest_paths, key=operator.itemgetter(1), \
            reverse=True)[:n]

def recursive_scan(this_dir, config, n_new, cata_list, site_navigation, genindex=True):
    """
    @this_dir starts inside docs, so you will never see 'docs/' in it. 
    @real_dir is @this_dir with a prefix, so we can list files done here
    @we use a @doc_path to indicate a logic log path, use @_doc_path to
    represent true path.

    also, we record the newest N blogs
    we use one single global_context to represent all files in the same dir
    """
    real_dir = os.path.join(config['docs_dir'], this_dir)
    scan_context = ScanContext(config, this_dir, site_navigation)

    global omit_path
    newest_paths = []
    local_paths = []
    dot_ignore = '.ignore'
    #globally ignore pages

    paths = os.listdir(real_dir)
    ignored_files = read_ignore(os.path.join(real_dir, dot_ignore))
    for f in paths:
        doc_path  = os.path.join(this_dir, f)
        _doc_path = os.path.join(real_dir, f)

        #locally ignored
        if f == dot_ignore:
            continue
        if f in ignored_files:
            continue
        if f in omit_path:
            continue
        #globally ingored
        if utils.is_page(doc_path, config['pages']):
            continue

        if utils.is_markdown_file(_doc_path) and utils.is_newmd(_doc_path):
#XXX: build page when it is new
            title = _build_blog(doc_path, config, scan_context)   
            addtime = os.path.getatime(_doc_path)

            local_paths.append((title, f, addtime))
            newest_paths.append((doc_path, addtime))

        elif os.path.isdir(_doc_path):
            sub_newest_paths = recursive_scan(doc_path, config, n_new,
                    cata_list, site_navigation)
#XXX: update top N pages
            newest_paths = add_top_n(newest_paths, sub_newest_paths, n_new)
        else:
            continue

        #now, we should generate a index.md for this dir
        #if this dir contains no markdowns, we don't generate index for it.
    if genindex == True and len(newest_paths) > 0:
        index_path = os.path.join(this_dir, 'index.md')
        index_title = parser.write_index(index_path, local_paths, config)
        _build_blog(index_path, config, scan_context)
#XXX: add to cata_list
        cata_list.append((index_title, this_dir))

    #XXX: restore context
    return add_top_n(newest_paths, [], n_new)




def build_blogs(config):
    topn = config.get('n_blogs_to_show') or 5
    cata_list = []
    site_navigation = nav.SiteNavigation(config)

    n_newest_path = newest_blogs = recursive_scan('.', config, 
            topn, cata_list, site_navigation, genindex=False)
    #write index.md and cata.md, since they are just [0] and [1] in the list, we
    #just need to do this
    print(config['pages'])
    parser.write_catalog(config, cata_list)
    parser.write_top_index(config, n_newest_path)

def build(config, live_server=False, clean_site_dir=False):
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


    log.debug("Building markdown pages.")

    #switch the build sequence, so that we can build catalist and index along
    #with pages
    build_blogs(config)
    build_pages(config)

    # NOW move compiled blogs along with themes to site dir
    # Reversed as we want to take the media files from the builtin theme
    # and then from the custom theme_dir so the custom versions take take
    # precedence.
    for theme_dir in reversed(config['theme_dir']):
        log.debug("Copying static assets from theme: %s", theme_dir)
        utils.copy_media_files(theme_dir, config['site_dir'])

    log.debug("Copying static assets from the docs dir.")
    utils.copy_media_files(config['docs_dir'], config['site_dir'])



from mkblogs import config
if __name__ == "__main__":
    logger = logging.getLogger('mkblogs')
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.DEBUG)

    config = config.load_config('tests/test_conf.yml')
    #print(config['pages'])
    #so basically you need add a '/' to urls, 
    build_blogs(config)
    build_pages(config)
