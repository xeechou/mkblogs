# coding: utf-8
from __future__ import print_function

from datetime import datetime

from jinja2.exceptions import TemplateNotFound
import mkblogs

from mkblogs import utils
from mkblogs.build import html as parser
from mkblogs.compat import urljoin, PY2
from mkblogs.relative_path_ext import RelativePathExtension, TitleExtension
from mkblogs.build import nav
import jinja2
import json
import markdown
import os
import logging
import operator
import threading
from multiprocessing import cpu_count as num_of_thread

from mkblogs.build.build_pages import *

log = logging.getLogger('mkblogs')
omit_path = ['index.md', 'img']


BLANK_BLOG_CONTEXT = {
        'page_title': None,
        'page_description': None,

        'content': None,
        'toc': None,
        'meta': None,


        'canonical_url': None,

        'current_page': None,   #remove this!!!!
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
    class BlogBuilder(threading.Thread):
        """
        A very thing layer of Thread object in so we can build object
        simoultaneously
        """
        def __init__(self, Context, tid):
            threading.Thread.__init__(self)
            self.context = Context
            self.tid = tid          #thread id

        def run(self):
            while True:
                blog_path = self.context.get_work()
                if not blog_path:
                    break
                #TODO: we should have something in return
                attrs = self.context.build_blog(blog_path, self.tid)
                self.context.done_work(blog_path, attrs)

    def __init__(self, config, tobuild):
        self.toupdate = utils.AtomicList(tobuild)
        self.updated  = utils.AtomicDict()
        self.config = config

        #XXX: step 1 setup n threads
        try:
            nthread = num_of_thread()
        except NotImplementedError:
            nthread = 4
        self.workers = []
        for i in range(nthread):
            self.workers.append(self.BlogBuilder(self, i))

        #XXX: step 2 generate context for building blogs
        self.site_navigation = nav.SiteNavigation(config['pages'])
        loader = jinja2.FileSystemLoader(config['theme_dir'])
        self.env = jinja2.Environment(loader=loader)
        dummy = os.path.join(config['docs_dir'], 'dummy')
        dummy_page = nav.Page(None, url=utils.get_url_path(dummy),
                path=dummy, url_context = nav.URLContext())
        self.site_navigation.update_path(dummy_page)

        #XXX: step 3. we have different context for every worker, so there will
        #be no data conflict
        self.global_context = []
        for i in range(nthread):
            self.global_context.append(get_global_context(self.site_navigation, config))

    def start(self):
        for t in self.workers:
            t.start()
        for t in self.workers:
            t.join()
        #build catalogs and something else

    def get_work(self):
        return self.toupdate.pop()
    def done_work(self, blog_path, attrs):
        #since for now, the only attrs is meta...
        meta = attrs['meta']
        info = []
        #because vals in meta is always dict, we get the first element
        info.append((meta.get('title') or meta.get('Title'))[0])
        info.append((meta.get('date')  or meta.get('Date'))[0])
        #except tags, they needs to be include
        info.append(meta.get('tags')  or meta.get('Tags'))
        self.updated[blog_path] = info

    def build_blog(self, path, tid):
        wanted_attrs = ['meta']
        unwanted_attrs = ['toc']
        return self._build_blog(path, self.config, tid,
                wanted_attrs, unwanted_attrs)

    def _build_blog(self, path, config, tid,
            wanted_attrs=[], unwanted_attrs=[]):
        """
        A generic _build_blog method, users can edit attribute themselves
        """
        input_path = os.path.join(config['docs_dir'], path)
        try:
            input_content = open(input_path, 'r').read()
        except IOError:
            log.error('file not found: %s', input_path)
            return
        if PY2:
            input_content = input_content.decode('utf-8')

        extens = config['markdown_extensions']

        html_content, toc, meta = parser.convert_markdown(
            input_content, #without site_navigation
            extensions=extens, strict=config['strict'], wantmd=False
        )

        context = self.global_context[tid]  #each thread has its our context
        context.update(BLANK_BLOG_CONTEXT)
        context.update(get_blog_context(config, html_content, toc, meta))

        #get what users wanted and remove want users dont wanted
        output_attrs = {}
        for i in wanted_attrs:
            output_attrs[i] = context.get(i)
        for i in unwanted_attrs:
            if not context.get(i):
                pass
            context[i] = None

        #Allow 'template:' override in md source files.
        if 'template' in meta:
            template = self.env.get_template(meta['template'][0])
        else:
            template = self.env.get_template('base.html')

        # Render the template.
        final_content =  template.render(context)
        #just write right in the directory
        output_path = os.path.splitext(input_path)[0] + '.html'
        with open(output_path, 'w') as f:
            f.write(final_content.encode('utf8'))
            f.close()

        return output_attrs


def get_toupdate(directory, config):
    #TODO:in the future version, we will allowed tree directory, using BFS
    dot_ignore = '.ignore'
    ignored_files = read_ignore(os.path.join(directory,\
        dot_ignore))
    ignored_files.append(dot_ignore)

    markdown_list = {}
    html_list = {}
    toupdate = []
    for f in os.listdir(directory):
        f_abs = os.path.join(directory, f)

        if f == dot_ignore:
            continue
        if f in ignored_files:
            continue
        if utils.is_page(f_abs, config['pages']):
            continue
        if utils.is_markdown_file(f):
            markdown_list[f] = os.path.getmtime(f_abs)
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

    return toupdate

def build_blogs(config):
    topn = config.get('n_blogs_to_show') or 5
    dot_record = config.get('dot_record') or '.record'

    #XXX:Step 1, get blog record, you will need it for updating catalogs
    blog_record = {}
    if os.path.isfile(os.path.join(config['docs_dir'],dot_record)):
        f = open(os.path.join(config['docs_dir'],dot_record))
        blog_record = json.loads(f.read())
        f.close()

    #XXX: Step 2, build all the blogs
    #FIXME: Fix this, if @blog_record is in anyway, missing something, the
    #generated catalog is incompleted
    toupdate = get_toupdate(config['docs_dir'], config)
    compiler = BlogsGen(config, toupdate)
    compiler.start()

    #XXX: Step 3, merge compiler.updated with dot_record
    for key in compiler.updated.keys():
        blog_record[key] = compiler.updated[key]
    #XXX: Step 4, generate catalogs with dot_record
    cata_list = {'default':[]}
    for key in blog_record.keys():
        tags = (blog_record[key])[-1]
        if not tags:
            cata_list['default'].append(key)
        for tag in tags:
            if not cata_list.get(tag):
                cata_list[tag] = [key]
            else:
                cata_list[tag].append(key)
    with open(os.path.join(config['docs_dir'],dot_record), 'w') as f:
        f.write(json.dumps(blog_record, ensure_ascii=False).encode('utf8'))
        f.close()
    #now we are done building all blogs, time to copy all html files to it.

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
    #change dir
    os.chdir('../sampleblog')
    config = config.load_config('mkblogs.yml')
    #so basically you need add a '/' to urls,
    build(config)
