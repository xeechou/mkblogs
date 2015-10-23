# coding: utf-8

"""
Standalone file utils.

Nothing in this module should have an knowledge of config or the layout
and structure of the site and pages in the site.
"""

import os
import shutil

from mkblogs.compat import urlparse


def copy_file(source_path, output_path):
    """
    Copy source_path to output_path, making sure any parent directories exist.
    """
    output_dir = os.path.dirname(output_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    shutil.copy(source_path, output_path)


def write_file(content, output_path):
    """
    Write content to output_path, making sure any parent directories exist.
    """
    output_dir = os.path.dirname(output_path)
    if not os.path.exists(output_dir):
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


def is_homepage(path):
    return os.path.splitext(path)[0] == 'index'


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
    for [path, name] in pages:
        if os.path.relpath(doc_path, path) == '.':
            return True
    return False




def create_media_urls(nav, url_list):
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
            relative_url = '%s/%s' % (nav.url_context.make_relative('/'), url)
            final_urls.append(relative_url)
    return final_urls


def create_relative_media_url(nav, url):
    """
    For a current page, create a relative url based on the given URL.

    On index.md (which becomes /index.html):
        image.png -> ./image.png
        /image.png -> ./image.png

    on sub/page.md (which becomes /sub/page.html):
        image.png -> ./image.png
        /image.png -> ./../image.png

    """

    # Allow links to fully qualified URL's
    parsed = urlparse(url)
    if parsed.netloc:
        return url

    # If the URL we are looking at starts with a /, then it should be
    # considered as absolute and will be 'relative' to the root.
    if url.startswith('/'):
        base = '/'
        url = url[1:]
    else:
        base = nav.url_context.base_path
    # base became himself, so first %s/ is just '.'
    relative_url = '%s/%s' % (nav.url_context.make_relative(base), url)

    # TODO: Fix this, this is a hack. Relative urls are not being calculated
    # correctly for images in the same directory as the markdown. I think this
    # is due to us moving it into a directory with index.html, but I'm not sure

    # TODO: I may want to get rid of below, transforming page.md to
    # page/index.html is too annoying
    #if nav.url_context.base_path is not '/' and relative_url.startswith("./"):
    #    relative_url = ".%s" % relative_url

    return relative_url

#these are for exclusive access
#XXX: maybe I should override python list and dict object?
class AtomicList(object):
    def __init__(self, toupdate = []):
        self.lock = threading.Lock()
        self.updatelist = toupdate

    def pop(self):
        self.lock.acquire()
        output = self.updatelist.pop() if self.updatelist else None
        self.lock.release()
        return output

    def push(self, update):
        self.lock.acquire()
        self.updatelist.append(update)
        self.lock.release()

class AtomicDict(object):
    def __init__(self, toupdate = {}):
        self.lock = threading.Lock()
        self.updatedict = toupdate

    def get(key):
        self.lock.acquire()
        val = self.updatedict.get(key)
        self.lock.release()
        return val
    def update(key, val):
        self.lock.acquire()
        val = self.updatedict[key] = val
        self.lock.release()
    #you could provide __getitem__ __setitem__

