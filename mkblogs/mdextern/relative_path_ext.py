"""
# Relative Path Markdown Extension

## Markdown URLs

Linking 'intro.md' to 'index.md' make intro.md to 'intro.html'

## Media URLs
To make it easier to work with media files and store them all
under one directory we re-write those to all be based on the
root. So, with the following markdown to add an image.

    ![The initial MkDocs layout](img/initial-layout.png)

The output would depend on the location of the Markdown file it
was added too.

Source file         | Url Path              | Image Path                   |
------------------- | --------------------- | ---------------------------- |
index.md            | index.html            | ./img/initial-layout.png     |
tutorial/install.md | tutorial/install.html | ./img/initial-layout.png     |
tutorial/intro.md   | tutorial/intro.html   | ./img/initial-layout.png     |

"""
from __future__ import print_function
import os
from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor

from mkblogs import utils
from mkblogs.compat import urlparse, urlunparse
from mkblogs.exceptions import MarkdownNotFound


def _iter(node):
    # TODO: Remove when dropping Python 2.6. Replace this
    # function call with note.iter()
    return [node] + node.findall('.//*')


def path_to_url(url, page, strict):
    """
    convert a path to valid url:
    1) if it is a media file, we change nothing
    2) if it is a md file, we make it to html file
    3) if it is url, we need to parse it
    """
    scheme, netloc, path, params, query, fragment = urlparse(url)

    if scheme or netloc or not path:
        # Ignore URLs unless they are a relative link to a markdown file.
        return url

    if page and not utils.is_markdown_file(path):
        path = utils.create_relative_media_url(page.url_context, path)
    elif page:
        target_file = page.file_context.make_absolute(path)
        if not os.path.exists(target_file):
            source_file = page.file_context.current_file
            msg = (
                #the actual problem is file_context, we cannot check if file
                #exits if it's path does not start in current dir
                'The page "%s" contained a hyperlink to "%s" which '
                'does not exist.'
            ) % (source_file, target_file)
            if strict:
                raise MarkdownNotFound(msg)
            else:
                print(msg)

        path = utils.get_url_path(target_file)
        path = page.url_context.make_relative(path)
    else:
        path = utils.get_url_path(path).lstrip('/')

    # Convert the .md hyperlink to a relative hyperlink to the HTML page.
    url = urlunparse((scheme, netloc, path, params, query, fragment))
    return url


class RelativePathTreeprocessor(Treeprocessor):

    def __init__(self, page, strict, prefix=None):
        self.this_page = page
        self.strict = strict
        #add a prefix to all url
        self.prefix = prefix

    def run(self, root):
        """Update urls on anchors and images to make them relative

        Iterates through the full document tree looking for specific
        tags and then makes them relative based on the site navigation
        """

        for element in _iter(root):

            if element.tag == 'a':
                key = 'href'
            elif element.tag == 'img':
                key = 'src'
            else:
                continue

            url = element.get(key)
            new_url = path_to_url(url, self.this_page, self.strict)
            if self.prefix:
                new_url = os.path.join(self.prefix, new_url)
            element.set(key, new_url)

        return root


class RelativePathExtension(Extension):
    """
    The Extension class is what we pass to markdown, it then
    registers the Treeprocessor.
    """

    def __init__(self, page, strict, prefix=None):
        self.this_page = page
        self.strict = strict
        self.prefix = prefix

    def extendMarkdown(self, md, md_globals):
        relpath = RelativePathTreeprocessor(self.this_page, self.strict, self.prefix)
        md.treeprocessors.add("relpath", relpath, "_end")

class TitleTreeprocessor(Treeprocessor):
    def run(self, root):
        """
        find first <h1> then set it, so later we can get it back
        """
        for element in _iter(root):
            if element.tag == 'h1':
                self.markdown.doc_title = element.text
                break
        return root

class TitleExtension(Extension):
    def extendMarkdown(self, md, md_globals):
        title = TitleTreeprocessor(md)
        md.treeprocessors.add("myTitle", title, "_end")

