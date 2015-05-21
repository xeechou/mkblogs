import os, operator
from lxml import etree
from mkblogs import utils, nav, toc
from mkblogs.relative_path_ext import RelativePathExtension
import markdown
import logging

"""
compiling functions
"""
def convert_markdown(markdown_source, site_navigation=None, extensions=(),
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
    mkblogs_extensions = [RelativePathExtension(site_navigation, strict), ]
    extensions = builtin_extensions + mkblogs_extensions + list(extensions)
    md = markdown.Markdown(
        extensions=extensions
    )
    html_content = md.convert(markdown_source)

    # On completely blank markdown files, no Meta or tox properties are added
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

def get_blog_title(config, path):
    """
    This is the best we can do to get blogs title. Since we cannot rely on
    anything else
    """
    title = ""
    print path
    with open(os.path.join(config['docs_dir'], path)) as f:
        for line in f:
            if line.startswith('#') and line[2] != '#':
                title = line[1:]
                break
        f.close()

    return title

def get_index_title(dirpath):
    name = os.path.basename(dirpath)
    if name:
        return name
    else:
        return 'Index'
    

def write_index(path, indices, config, title=None):
    """
    write @indices to @path, generate title if not provided
    @blog_path is just a name, means you want open it, u need 
    os.path.join(path, blog_path)
    """
    if not title:
        dirname = get_located_path(path)
        if dirname:
            title = nav.filename_to_title(dirname)
        else:
            title = 'Index'

    #sort indices
    sorted_inds = sorted(indices, key=operator.itemgetter(1))
    with open(os.path.join(config['docs_dir'], path), 'w') as f:
        f.write("#{}\n".format(title))
        f.write("\n")
        for (blog_path, build_time) in sorted_inds:
            name = get_blog_title(config, blog_path)
            f.write("*  [{0}]({1})\n".format(name, os.path.basename(blog_path)))
        f.close()
    return title

def write_catalog(config, catalist):
    """
    write the top catalog page for blogs according to catalist,
    catalist is list of dirnames, in mkblogs's scenario, it will treat dirname as
    actual file, and transfer to 'dirname/index.md', which points to exact
    location of the index file. If using our senario, we will treat it as dir,
    then it points to dirname.
    """
    cata_path = config['pages'][1][0]
    path = os.path.join(config['docs_dir'], cata_path)
    with open(path, 'w') as f:
        for (name, index_path) in catalist:
            if not name:
                name = nav.filename_to_title(index_path)
            f.write("*  [{0}]({1})\n".format(name, index_path))
        f.close()



#Code Block for writing THE index.html
#we use xml parser, since python-markdown doesn't generate complete html file
# markdown is compatible to html code, so we can just operate on generated
# html code, you know, relocate the images.

## some constant, first line break:
line_seperator = "\n-------------------------------------\n"

class ContentParser:
    def __init__(self, config):
	self.root_path = config['docs_dir']
        self.extensions = config['markdown_extensions']

    def merge_htmls(self, head_list):
	whole_md = ""
	global line_seperator

	for html in head_list:
	    whole_md += html
	    whole_md += line_seperator
        whole_md = whole_md[:-len(line_seperator)]
        return whole_md

    def get_heads(self, md_path, nlines):
        """
        get n lines from file @md_path and translate it, relocate the image
        accordingly
        """
        if nlines <= 0:
            return None

        rel_path = os.path.dirname(md_path)         #rel_path could be ''

        md_src = ""
	""" 
	This is our current approach, a better method needs match the indention
	depth for last few lines, so we not encounter any sudden break
	"""

        with open(os.path.join(self.root_path, md_path)) as f:
            for i in range(nlines):
                md_src += f.readline()
            f.close()
	md_src = md_src.decode('utf-8')
        (html, toc, meta) = convert_markdown(md_src, extensions= self.extensions)

	tree = etree.fromstring(u'<html>'+html+u'</html>')

	titles = tree.xpath("//h1")
	if len(titles) > 1:
		raise NameError("Multiple titles")
	title = titles[0].text

	"""Now we relocate the images"""
	relocate_list = tree.xpath("//img")
        relocate_list.extend(tree.xpath("//a"))

	for element in relocate_list:
            if element.tag == 'a':  #<a href>
                key = 'href'
                to_replace = element.attrib['href']
                to_replace = utils.get_html_path(to_replace)
            else:
                key = 'src'         #<img src>
	        to_replace = element.attrib['src']

            if to_replace.startswith('/'):
                to_replace = to_replace[1:]
            else:
		to_replace = os.path.join(rel_path, to_replace)
		
	    element.attrib[key] = to_replace

        readmore = utils.get_html_path(md_path)
        #TODO: add a readmore in the text
	return ContentParser.__remove__html_tag(\
			etree.tostring(tree, encoding='utf-8')) +\
                    "\n[Read More]({})\n".format(readmore)
    @staticmethod
    def __remove__html_tag(string):
	""" remove the <html> </html> tags at head and tail """

	if string.startswith('<html>'):
	    string = string[6:]
	if string.endswith('</html>'):
	    string = string[:-7]
	return string

def write_top_index(config, newest_path):
    index_generator = ContentParser(config)
    index_content = []
    for i in newest_path:
        index_content.append(index_generator.get_heads(i[0], 20))

    index_content = index_generator.merge_htmls(index_content)

    with open(os.path.join(config['docs_dir'], 'index.md'), 'w') as f:
        f.write(index_content)
        f.close()


if __name__ == "__main__":
    """
    unit test
    """
    #1) write_index test.
    file_path= 'docs/Cluster'
    indices = [ ('Title0', '/tmp/sample/sample0', 110),
                ('Title1', '/tmp/sample/sample1', 111),
                ('Title2', '/tmp/sample/sample2', 112),
                ('Title3', '/tmp/sample/sample3', 113),
                ('Title4', '/tmp/sample/sample4', 114),
                ('Title5', '/tmp/sample/sample5', 115),
                ('Title6', '/tmp/sample/sample6', 116),
                ('Title7', '/tmp/sample/sample7', 117),
                ('Title8', '/tmp/sample/sample8', 118)]
    path = '/tmp/sample'
    write_index(path, indices)
