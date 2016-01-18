import os, operator
from mkblogs import utils, toc
from mkblogs.build import nav
from mkblogs.mdextern import RelativePathExtension
import markdown
import logging

"""
compiling functions
"""
def convert_markdown(markdown_source, page=None, extensions=(),
        strict=False, wantmd=False):
    """
    Convert the Markdown source file to HTML content, and additionally
    return the parsed table of contents, and a dictionary of any metadata
    that was specified in the Markdown file.

    `extensions` is an optional sequence of Python Markdown extensions to add
    to the default set.
    """

    # Generate the HTML from the markdown source
    builtin_extensions = ['meta', 'toc', 'tables', 'fenced_code']
    mkblogs_extensions = [RelativePathExtension(page, strict), ]
    extensions = builtin_extensions + mkblogs_extensions + list(extensions)
    md = markdown.Markdown(
        extensions=extensions
    )
    html_content = md.convert(markdown_source)

    # On completely blank markdown files, no Meta or toc properties are added
    # to the generated document.
    meta = getattr(md, 'Meta', {})
    toc_html = getattr(md, 'toc', '')

    # Post process the generated table of contents into a data structure
    table_of_contents = toc.TableOfContents(toc_html)

    if wantmd:
        return (html_content, table_of_contents, meta, md)
    else:
        return (html_content, table_of_contents, meta)


def get_located_path(file_path):
    """
    get a file's located dir from its abs_path file_name. If we only get a file_name
    provided, the result will be ''
    """
    return os.path.basename(os.path.dirname(file_path))


def get_index_title(dirpath):
    name = os.path.basename(dirpath)
    if name:
        return name
    else:
        return 'Index'

