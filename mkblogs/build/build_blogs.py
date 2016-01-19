# coding: utf-8
from __future__ import print_function

from datetime import datetime

from jinja2.exceptions import TemplateNotFound
import mkblogs

from mkblogs import utils
from mkblogs.build import html as parser
from mkblogs.compat import urljoin, PY2
from mkblogs.build import nav
import jinja2
import json
import markdown
import os
import logging
import operator
import threading
from multiprocessing import cpu_count as num_of_thread

from mkblogs.build.build_pages import build_pages, get_global_context, \
        site_directory_contains_stale_files,\
        build_catalog, build_index

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
def get_global_blog_context(blog, site_navigation, config):
    """
    This is a temporary hack, because we need different context different where,
    so we need set_abs then set it back, we may just use different context later
    """
    blog.set_abs(config['docs_dir'],config['site_dir'])
    context = get_global_context(blog, site_navigation, config)
    blog.set_rel()
    return context


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
                blog = self.context.setup_page(blog_path, self.tid)
                attrs = self.context.build_blog(blog, self.context.site_navigation)
                self.context.done_work(blog_path, attrs)
    #XXX:init function fixed.
    def __init__(self, config, tobuild, site_navigation):
        self.toupdate = utils.AtomicList(tobuild)
        self.updated  = utils.AtomicDict()
        self.config = config
        self.blogs = []

        #XXX: step 1 setup n threads
        try:
            nthread = num_of_thread()
        except NotImplementedError:
            nthread = 4
        self.workers = []
        for i in range(nthread):
            self.workers.append(self.BlogBuilder(self, i))

        #XXX: step 2 generate context for building blogs
        self.site_navigation = site_navigation
        loader = jinja2.FileSystemLoader(config['theme_dir'])
        self.env = jinja2.Environment(loader=loader)
        dummy = os.path.join(config['docs_dir'], 'dummy')

        #XXX: step 3. we have different context for every worker, so there will
        #be no data conflict
        for i in range(nthread):
            self.blogs.append(nav.Blog(dummy,dummy))

    def setup_page(self, blog_path, tid):
        blog = self.blogs[tid]
        blog.set_pathurl(blog_path)
        return blog

    def start(self):
        for t in self.workers:
            t.start()
        for t in self.workers:
            t.join()
        #build catalogs and something else

    def get_work(self):
        return self.toupdate.pop()
    def done_work(self, blog_path, attrs):
        info = []
        info.append(attrs['page_title'])
        info.append(attrs['page_date'] )
        info.append(attrs['page_tags'] )
        self.updated[blog_path] = info

    def build_blog(self, blog,site_navigation):
        wanted_attrs = ['page_date', 'page_title', 'page_tags']
        unwanted_attrs = ['toc']
        return self._build_blog(blog, self.config, site_navigation,
                wanted_attrs, unwanted_attrs)
    #XXX:fixed
    def _build_blog(self, blog, config, site_navigation,
            wanted_attrs=[], unwanted_attrs=[]):
        """
        A generic _build_blog method, users can edit attribute themselves
        """
        input_path = os.path.join(config['docs_dir'],blog.input_path)
        output_path = os.path.join(config['docs_dir'], blog.output_path)

        try:
            input_content = open(input_path, 'r').read()
        except IOError:
            log.error('file not found: %s', input_path)
            return
        if PY2:
            input_content = input_content.decode('utf-8')

        extens = config['markdown_extensions']

        html_content, toc, meta = parser.convert_markdown(
            input_content, page=blog,
            extensions=extens, strict=config['strict'])
        #every thread has its our context
        context = get_global_blog_context(blog, site_navigation, config)
        context.update(BLANK_BLOG_CONTEXT)
        context.update(get_blog_context(config, html_content, toc, meta))

        #get what users wanted and remove want users dont wanted
        #so in general, toc is removed
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

        with open(output_path, 'w') as f:
            f.write(final_content.encode('utf8'))
            f.close()

        return output_attrs


def get_blog_context(config, html, toc, meta):
    """
    update a blogs' page context
    """
    try:
        title = (meta.get('title') or meta.get('Title'))[0]
        date = (meta.get('date') or meta.get('Date'))[0]
    except:
        raise NameError('Error in retrieving blogs meta')

    date = utils.parse_date(date)
    tags = meta.get('tags') or meta.get('Tags')
    if not tags:
        tags = ['TO TAGS']

    return {
            #there is no next page and previous page for blo
            'content' : html,
            'toc' : toc,
            'meta' : meta,
            'page_title' : title,
            'page_date' : date,
            'page_tags' : tags
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
        if os.path.isdir(f_abs):
            continue
        if utils.is_newmd(f_abs):   #change is to is new_md
            toupdate.append(f)

    return toupdate

def build_blogs(config, site_navigation):
    """
    build blogs and generate enough information for build pages
    """
    topn = config.get('n_blogs_to_show') or 5
    dot_record = config.get('dot_record') or '.record'

    #XXX:Step 1, get blog record, you will need it for updating catalogs
    blog_record = utils.load_json(os.path.join(config['docs_dir'],dot_record))

    #XXX: Step 2, build all the blogs
    #FIXME: Fix this, if @blog_record is in anyway, missing something, the
    #generated catalog is incompleted
    toupdate = get_toupdate(config['docs_dir'], config)
    compiler = BlogsGen(config, toupdate, site_navigation)
    compiler.start()

    #XXX: Step 3, merge compiler.updated with dot_record
    blog_record.update(compiler.updated)
    utils.write_json(os.path.join(config['docs_dir'],dot_record), blog_record)

    #XXX: Step 4, generate catalogs and index
    config['catalist'] = gen_catalist(blog_record)
    config['blogs_on_index'] = utils.sort_blogs(blog_record)[:topn]

def gen_catalist(record):
    cata_list = {}
    for key in record.keys():
        tags = (record[key])[-1]
        for tag in tags:
            if not cata_list.get(tag):
                cata_list[tag] = [(record[key][0], key)]
            else:
                cata_list[tag].append((record[key][0], key))
    return cata_list

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
    site_navigation = nav.SiteNavigation(config['pages'])
    log.debug("Building blogs.")
    build_blogs(config, site_navigation)
    log.debug("Building markdown pages.")
    build_pages(config, site_navigation)

    # NOW move compiled blogs along with themes to site dir
    # Reversed as we want to take the media files from the builtin theme
    # and then from the custom theme_dir so the custom versions take take
    # precedence.
    for theme_dir in reversed(config['theme_dir']):
        log.debug("Copying static assets from theme: %s", theme_dir)
        utils.copy_media_files(theme_dir, '')

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
