# coding: utf-8

"""
Standalone file utils.

Nothing in this module should have an knowledge of config or the layout
and structure of the site and pages in the site.
"""

import os
import shutil
import operator
import time
import json

from mkblogs import exceptions
from mkblogs.compat import urlparse
from dateutil.parser import parse as _parse_date
from datetime import datetime
import threading

def parse_date(date_string):
    #FIXME: argument must 9 item sequence, not datetime datetime
    return _parse_date(date_string).strftime("%d %b %Y")

def sort_blogs(dic):
    to_sort = [(x, time.mktime(_parse_date(dic[x][1]).timetuple()) ) for x in dic.keys()]
    sorted_blogs = sorted(to_sort, key=operator.itemgetter(1))
    return [x[0] for x in sorted_blogs]


def copy_file(source_path, output_path):
    """
    Copy source_path to output_path, making sure any parent directories exist.
    """
    output_dir = os.path.dirname(output_path)
    if output_dir == '' or os.path.exists(output_dir):
        pass
    else:
        os.makedirs(output_dir)
    shutil.copy(source_path, output_path)


def write_file(content, output_path):
    """
    Write content to output_path, making sure any parent directories exist.
    """
    output_dir = os.path.dirname(output_path)
    if output_dir == '' or os.path.exists(output_dir):
        pass
    else:
        os.makedirs(output_dir)
    open(output_path, 'wb').write(content)


def clean_directory(directory):
    """
    Remove the content of a directory recursively but not the directory itself.
    """
    if not os.path.exists(directory):
        return

    for entry in os.listdir(directory):

        # Don't remove hidden files from the directory. We never copy files
        # that are hidden, so we shouldn't delete them either.
        if entry.startswith('.'):
            continue

        path = os.path.join(directory, entry)
        if os.path.isdir(path):
            shutil.rmtree(path, True)
        else:
            os.unlink(path)


def copy_media_files(from_dir, to_dir):
    """
    Recursively copy all files except markdown into another directory.
    """
    for (source_dir, dirnames, filenames) in os.walk(from_dir):
        relative_path = os.path.relpath(source_dir, from_dir)
        output_dir = os.path.normpath(os.path.join(to_dir, relative_path))

        # Filter filenames starting with a '.'
        filenames = [f for f in filenames if not f.startswith('.')]

        # Filter the dirnames that start with a '.' and update the list in
        # place to prevent us walking these.
        dirnames[:] = [d for d in dirnames if not d.startswith('.')]

        for filename in filenames:
            if not is_markdown_file(filename):
                source_path = os.path.join(source_dir, filename)
                output_path = os.path.join(output_dir, filename)
                copy_file(source_path, output_path)


def get_html_path(path):
    """
    Map a source file path to an output html path.

    Paths like 'index.md' will be converted to 'index.html'
    Paths like 'api-guide/core.md' will be converted to 'api-guide/core.html'
    """
    path = os.path.splitext(path)[0]
    return path + '.html'

def get_url_path(path):
    """
    Map a source file path to an output html path.

    Paths like 'index.md' will be converted to '/index.html'
    Paths like 'about.md' will be converted to '/about.html'
    Paths like 'api-guide/core.md' will be converted to '/api-guide/core.html'

    """
    path = get_html_path(path)
    url = '/' + path.replace(os.path.sep, '/')
    return url
def has_template(d):
    for f in d:
        if is_html_file(f):
            return True
    return False

def exact_page_config(config_line):
    #this is not what we wanted, Another day
    if isinstance(config_line, str):
        path = config_line
        title, child_title = None, None
    elif len(config_line) in (1, 2, 3):
        # Pad any items that don't exist with 'None'
        padded_config = (list(config_line) + [None, None])[:3]
        path, title, child_title = padded_config
    else:
        msg = (
            "Line in 'page' config contained %d items.  "
            "Expected 1, 2 or 3 strings." % len(config_line)
        )
        raise exceptions.ConfigurationError(msg)
    return path, title, child_title

def is_homepage(path):
    return os.path.splitext(path)[0] == 'index'
def is_catalog(path):
    name = os.path.splitext(path)[0]
    return name == 'catalog' or name == 'Catalog'\
        or name == 'catalogs' or name == 'Catalogs'


def is_markdown_file(path):
    """
    Return True if the given file path is a Markdown file.

    http://superuser.com/questions/249436/file-extension-for-markdown-files
    """
    ext = os.path.splitext(path)[1].lower()
    return ext in [
        '.markdown',
        '.mdown',
        '.mkdn',
        '.mkd',
        '.md',
    ]


def is_css_file(path):
    """
    Return True if the given file path is a CSS file.
    """
    ext = os.path.splitext(path)[1].lower()
    return ext in [
        '.css',
    ]


def is_javascript_file(path):
    """
    Return True if the given file path is a Javascript file.
    """
    ext = os.path.splitext(path)[1].lower()
    return ext in [
        '.js',
        '.javascript'
    ]


def is_html_file(path):
    """
    Return True if the given file path is an HTML file.
    """
    ext = os.path.splitext(path)[1].lower()
    return ext in [
        '.html',
        '.htm',
    ]

def is_newmd(doc_path):
    """
    test if @doc_path worth compiling
    @doc_path has to exists
    """
    if not is_markdown_file(doc_path):
        return False
    html_path  = os.path.splitext(doc_path)[0] + '.html'

    if not os.path.exists(html_path):
        return True
    doc_mtime  = os.path.getmtime(doc_path)
    html_mtime = os.path.getmtime(html_path)
    return True if doc_mtime > html_mtime else False


def is_page(doc_path, pages):
    """
    will not work in this case:
    in someplace
    a = ../someplace/aaa.md
    b = aaa.md
    """
    for page in pages:
        path, title, child_title = exact_page_config(page)
        if path == doc_path:
            return True
    return False


def create_media_urls(url_context, url_list):
    """
    Return a list of URLs that have been processed correctly for inclusion in a page.
    """
    final_urls = []
    for url in url_list:
        # Allow links to fully qualified URL's
        parsed = urlparse(url)
        if parsed.netloc:
            final_urls.append(url)
        else:
            relative_url = '%s/%s' % (url_context.make_relative('/'), url)
            final_urls.append(relative_url)
    return final_urls


#TODO: change nav to url context
def create_relative_media_url(url_context, url):
    """
    On index.md (which becomes /index.html):
        image.png -> ./image.png
        /image.png -> ./image.png

    on sub/page.md (which becomes /sub/page.html):
        image.png -> ./image.png
        /image.png -> ./../image.png
    """
    parsed = urlparse(url)
    if parsed.netloc:
        return url
    relative_path = './%s' % url_context.make_relative(url) 

    return relative_path

def load_json(filename):
    jsonobj = {}
    if os.path.isfile(filename):
        f = open(filename, 'r')
        try:
            jsonobj = json.loads(f.read())
        except: #if the file is corrupted, we just ignore it, we will write it
                #again anyway
            print("Warning: corrupted json file")
        f.close()
    return jsonobj

def write_json(filename, obj):
    with open(filename, 'w') as f:
        f.write(json.dumps(obj, ensure_ascii=False).encode('utf8'))
        f.close()

class AtomicList(list):
    def __init__(self, *args):
        self.lock = threading.Lock()
        super(AtomicList, self).__init__(*args)

    def pop(self, ind=-1):
        self.lock.acquire()
        output = None
        if self:
            output = super(AtomicList, self).pop(ind)
        self.lock.release()
        return output
    #XXX: to be more rubust, you need try catch, but...
    def __getitem__(self, key):
        self.lock.acquire()
        output = super(AtomicList, self).__getitem__(key)
        self.lock.release()
        return output
    def __setitem__(self, key, item):
        self.lock.acquire()
        super(AtomicList, self).__setitem__(key, item)
        self.lock.release()

    def append(self, val):
        self.lock.acquire()
        super(AtomicList, self).append(val)
        self.lock.release()

class AtomicDict(dict):
    def __init__(self, *args):
        self.lock = threading.Lock()
        super(AtomicDict, self).__init__(args)

    def __getitem__(self, key):
        self.lock.acquire()
        val = super(AtomicDict, self).get(key)
        self.lock.release()
        return val

    def __setitem__(self, key, val):
        self.lock.acquire()
        val = super(AtomicDict, self).__setitem__(key, val)
        self.lock.release()
    #you could provide __getitem__ __setitem__


#import random
#class simple_thread(threading.Thread):
#    def __init__(self, l):
#        self.l = l
#        threading.Thread.__init__(self)
#    def run(self):
#        while True:
#            if self.l:
#                self.l.pop()
#            self.l.append(random.random())
#
#if __name__ == "__main__":
#    a = AtomicList()
#    if a:
#        print(a)
#    a.pop()
#    threads = []
#    for i in range(10):
#        threads.append(simple_thread(a))
#    for i in range(10):
#        threads[i].start()
#    for i in range(10):
#        threads[i].join()
#if __name__ == "__main__":
#    import json
    #with open('sampleblog/docs/.record') as f:
    #    jsonobj = json.loads(f.read())
    #    f.close()
    #print()
