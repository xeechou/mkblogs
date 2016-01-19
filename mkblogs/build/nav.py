# coding: utf-8

"""
Deals with generating the site-wide navigation.

This consists of building a set of interlinked page and header objects.
"""

from mkblogs import utils, exceptions
import posixpath
import os


def filename_to_title(filename):
    """
    Automatically generate a default title, given a filename.
    """
    if utils.is_homepage(filename):
        return 'Home'

    title = os.path.splitext(filename)[0]
    title = title.replace('-', ' ').replace('_', ' ')
    # Captialize if the filename was all lowercase, otherwise leave it as-is.
    if title.lower() == title:
        title = title.capitalize()
    return title

class SiteNavigation(object):
    def __init__(self, pages_config):
        self.nav_items, self.pages = \
            _generate_site_navigation(pages_config)
        self.homepage = self.pages[0] if self.pages else None

    def __str__(self):
        return ''.join([str(item) for item in self])

    def __iter__(self):
        return iter(self.nav_items)

    #make every page has their own url_context
    def update_path(self, page):
        page.set_active()

    def get_page(self, name):
        for page in self.pages:
            if page.title == name:
                return page
        return None


    def walk_pages(self):
        """
        Returns each page in the site in turn.

        Additionally this sets the active status of the pages and headers,
        in the site navigation, so that the rendered navbar can correctly
        highlight the currently active page and/or header item.
        """
        page = self.homepage
        self.update_path(page)
        yield page
        while page.next_page:
            page.set_active(False)
            page = page.next_page
            self.update_path(page)
            yield page
        page.set_active(False)

    @property
    def source_files(self):
        if not hasattr(self, '_source_files'):
            self._source_files = set([page.input_path for page in self.pages])
        return self._source_files
    def page_template(self, page):
        return None

#TODO: fix this two
class URLContext(object):
    """
    The URLContext is used to ensure that we can generate the appropriate
    relative URLs to other pages from any given page in the site.

    The problem we have is relative_url has too many problem, I cannot make
    relative to a dynamic url and static url(eg: docs/some.md and /image.png)
    """

    def __init__(self):
        self.base_path = '/'

    def set_current_url(self, current_url):
        self.base_path = posixpath.dirname(current_url)

    def make_relative(self, url):
        """
        return the relative url of an ABS URL to base_path
        """
        if url.startswith('/'):
            base_path = '/' + self.base_path.lstrip('/')
            relative_path = posixpath.relpath(url, start=base_path)
        else:   #it is relative url already
            relative_path = url

        return relative_path


class FileContext(object):
    """
    The FileContext is used to ensure that we can generate the appropriate
    full path for other pages given their relative path from a particular page.

    This is used when we have relative hyperlinks in the documentation, so that
    we can ensure that they point to markdown documents that actually exist
    in the `pages` config.

    But it only works if have correct file context
    """
    def __init__(self):
        self.current_file = None
        self.base_path = ''

    def set_current_path(self, current_path):
        self.current_file = current_path
        self.base_path = os.path.dirname(current_path)

    def make_absolute(self, path):
        """
        Given a relative file path return it as a POSIX-style
        absolute filepath, given the context of the current page.
        """
        return posixpath.normpath(posixpath.join(self.base_path, path))

class Blog(object):
    def __init__(self, url, path):
        self.abs_url = url
        self.url_context = URLContext()
        self.file_context = FileContext()

        self.input_path = path
        self.output_path = utils.get_html_path(path)
        self.file_context.set_current_path(path)
        self.url_context.set_current_url(url)

    def set_pathurl(self, path):
        self.abs_url = utils.get_url_path(path)
        self.input_path = path
        self.output_path = utils.get_html_path(path)
        self.file_context.set_current_path(path)
        self.url_context.set_current_url(utils.get_url_path(path))

    def set_abs(self, docs_dir, site_dir):
        self.file_context.set_current_path(\
                os.path.join(docs_dir, self.input_path))
        self.url_context.set_current_url(\
                os.path.join(site_dir, self.output_path))

    def set_rel(self):
        self.file_context.set_current_path(self.input_path)
        self.url_context.set_current_url(self.output_path)

class Page(Blog):
    def __init__(self, title, url, path):
        super(Page, self).__init__(url, path)
        self.title = title
        self.active = False
        self.func = None

        # Links to related pages
        self.previous_page = None
        self.next_page = None
        self.ancestors = []

    @property
    def url(self):
        return self.url_context.make_relative(self.abs_url)

    @property
    def is_homepage(self):
        return utils.is_homepage(self.input_path)

    def __str__(self):
        return self._indent_print()

    def _indent_print(self, depth=0):
        indent = '    ' * depth
        active_marker = ' [*]' if self.active else ''
        title = self.title if (self.title is not None) else '[blank]'
        return '%s%s - %s%s\n' % (indent, title, self.abs_url, active_marker)

    def set_active(self, active=True):
        self.active = active
        for ancestor in self.ancestors:
            ancestor.active = active

    def set_builder(self, build_func):
        self.func = build_func
    def get_builder(self):
        return self.func


class Header(object):
    def __init__(self, title, children):
        self.title, self.children = title, children
        self.active = False

    def __str__(self):
        return self._indent_print()

    def _indent_print(self, depth=0):
        indent = '    ' * depth
        active_marker = ' [*]' if self.active else ''
        ret = '%s%s%s\n' % (indent, self.title, active_marker)
        for item in self.children:
            ret += item._indent_print(depth + 1)
        return ret


def _generate_site_navigation(pages_config):
    """
    Returns a list of Page and Header instances that represent the
    top level site navigation.
    """
    nav_items = []
    pages = []
    previous = None

    #TODO: ad new version config
    for config_line in pages_config:
        path, title, child_title = utils.exact_page_config(config_line)

        # If both the title and child_title are None, then we
        # have just been given a path. If that path contains a /
        # then lets automatically nest it.
        if title is None and child_title is None and os.path.sep in path:
            filename = path.split(os.path.sep)[-1]
            child_title = filename_to_title(filename)

        if title is None:
            filename = path.split(os.path.sep)[0]
            title = filename_to_title(filename)

        url = utils.get_url_path(path)

        if not child_title:
            # New top level page.
            page = Page(title=title, url=url, path=path)
            nav_items.append(page)
        elif not nav_items or (nav_items[-1].title != title):
            # New second level page.
            page = Page(title=child_title, url=url, path=path)
            header = Header(title=title, children=[page])
            nav_items.append(header)
            page.ancestors = [header]
        else:
            # Additional second level page.
            page = Page(title=child_title, url=url, path=path)
            header = nav_items[-1]
            header.children.append(page)
            page.ancestors = [header]

        # Add in previous and next information.
        if previous:
            page.previous_page = previous
            previous.next_page = page
        previous = page

        pages.append(page)

    return (nav_items, pages)

if __name__ =='__main__':
    from mkblogs.utils import create_relative_media_url

    url_context = URLContext()
    url_context.set_current_url('docs/anotherdoc.html')
    print(url_context.make_relative('/'))

