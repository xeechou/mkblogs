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
import threading
from multiprocessing import cpu_count as num_of_thread

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

def get_blog_context(config, html, toc, meta):
    """
    update a blogs' page context
    """
    return {

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

class BlogsGen(object):
    """
    BlogsGenerator provides all the context for compile every blog,
    it will also generate tags pages.
    """
    class UpdateList(object):
        def __init__(self, toupdate = None):
            self.lock = threading.Lock()
            self.updatelist = toupdate if toupdate != None else []

        def get_to_build(self):
            self.lock.acquire()
            output = self.updatelist.pop() if self.updatelist else None
            self.lock.release()
            return output

        def done_build(self, update):
            self.lock.acquire()
            self.updatelist.append(update)
            self.lock.release()

    class BlogBuilder(threading.Thread):
        """
        A very thing layer of Thread object in so we can build object
        simoultaneously
        """
        def __init__(self, Context):
            threading.Thread.__init__(self)
            self.context = Context

        def run(self):
            while True:
                output = self.Context.get_to_build()
                if not ouput:
                    break
                self.Context.build_blog(output)


    def __init__(self, config, tobuild):
        self.toupdate = UpdateList(tobuild)
        self.updated  = UpdateList()
        self.config = config
        #TODO: fix the line below
        self.scan_context = ScanContext(config['docs_dir'])

        try:
            nthread = num_of_thread()
        except NotImplementedError:
            nthread = 4
        self.workers = []
        for i in [0:nthread]:
            self.workers.append(BlogBuilder(self))

    def start(self):
        for t in self.workers:
            t.start()
        for t in self.workers:
            t.join()
        #build something else

    def get_to_build(self):
        return self.toupdate.get_to_build()
    def done_build(self):
        self.updated.done_build()

    def build_blog(self, path):
        self._build_blog(path, self.config, scan_context)

    def _build_blog(self, path, config, scan_context):
        """
        convert a blog from @input_path to @output_path html, this function
        differs from _build_page where it use a page struct.
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

        html_content, toc, meta = parser.convert_markdown(
            input_content, #without site_navigation
            extensions=extens, strict=config['strict'], wantmd=False
        )

        #if we want to parallize, we have to acquire a lock for global_context
        context = scan_context.global_context
        context.update(BLANK_BLOG_CONTEXT)
        context.update(get_blog_context(config, html_content, toc, meta))

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


def get_toupdate(directory):
    dot_ignore = '.ignore'
    ignored_files = read_ignore(os.path.join(directory,\
        dot_ignore)).append(dot_ignore)

    markdown_list = {}
    html_list = {}
    toupdate = []
    for f in os.listdir(directory):
        f_abs = os.path.join(directory, f)

        if f == dot_ignore:
            continue
        if f in ignored_files:
            continue
        if utils.is_page(config['pages']):
            continue
        if utils.is_markdown_file(f):
            markdown_list[f] = os.path.getmtime(f_abs)
        #XXX: this could be images, assets or something
        if utils.is_html_file(f):       #we dont care what the generated html extension is
            html_list[os.path.splitext(f)[0]] = os.path.getmtime(f_abs)
        if os.path.isdir(f_abs):
            continue

    for key in markdown_list.keys():
        name = os.path.splitext(key)[0]
        mtime = markdown_list[key]
        if not html_list.get(name):
            toupdate.append(key)
        elif html_list.get(name) < mtime:
            toupdate.append(key)
        else: #html_list.get(name) >= mtime
            continue
    #del markdown_list
    #del html_list
    return toupdate

def build_blogs(config):
    topn = config.get('n_blogs_to_show') or 5
    #if I have record for previous blogs, I will be so happy
    dot_record = config.get('dot_record') or '.record'
    blog_record = []
    if os.isfile(os.path.join(config['docs_dir'],dot_record)):
        f = open(os.path.join(config['docs_dir'],dot_record))
        blog_record = json.loads(f.read())
        f.close()
    toupdate = get_toupdate(config['docs_dir'])
    #what I need to do now is get a builder that are generic enough

    cata_list = []
    site_navigation = nav.SiteNavigation(config['pages'])


    n_newest_path = newest_blogs = recursive_scan('.', config,
            topn, cata_list, site_navigation, genindex=False)
    #write index.md and cata.md, since they are just [0] and [1] in the list, we
    #just need to do this
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



    #switch the build sequence, so that we can build catalist and index along
    #with pages
    log.debug("Building blogs.")
    build_blogs(config)
    log.debug("Building markdown pages.")
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
    build(config)
