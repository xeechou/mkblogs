import os, operator
from mkblogs import utils, nav
from mkblogs.relative_path_ext import RelativePathExtension

"""
compiling functions
"""
def convert_markdown(markdown_source, site_navigation=None, extensions=(), strict=False):
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

    return (html_content, table_of_contents, meta)


def get_located_path(file_path):
    """
    get a file's located dir from its abs_path file_name. If we only get a file_name
    provided, the result will be ''
    """
    return os.path.basename(os.path.dirname(file_path))

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
    sorted_inds = sorted(indices, key=operator.itemgetter(2))
    with open(os.path.join(config['docs_dir'], path), 'w') as f:
        f.write("#{}\n".format(title))
        f.write("\n")
        for (name, blog_path, build_time) in sorted_inds:
            f.write("*  [{0}]({1})\n".format(name, blog_path))
        f.close()

def write_catalog(config, catalist):
    """
    write the top catalog page for blogs according to catalist,
    catalist is list of dirnames, in mkblogs's scenario, it will treat dirname as
    actual file, and transfer to 'dirname/index.md', which points to exact
    location of the index file. If using our senario, we will treat it as dir,
    then it points to dirname.
    """
    cata_path = config['pages'][1][0]
    path = os.join(config['docs_dir'], cata_path)
    with open(path, 'w') as f:
        for (name, index_path) in catalist:
            f.write("*  [{0}]({1})\n".\
                    format(name, os.path.relpath(index_path, cata_path)))
        f.close()

#we use xml parser, since python-markdown doesn't generate complete html file

# Another thing I want to mention here: 
# markdown is compatible to html code, so we can just operate on generated
# html code, you know, relocate the images. Awesome.

## some constant, first line break:
line_seperator = "\n-------------------------------------\n"

class ContentParser:
    def __init__(self, curr_dir):
        if not os.path.isabs(curr_dir) or not os.path.isdir(curr_dir):
		raise NameError('Unsupport')
	self.curr_dir = curr_dir

    def merge_htmls(self, head_list):
	whole_md = ""
	global line_seperator

	for (html, head) in head_list:
	    whole_md += html
	    whole_md += line_seperator
	whole_md -= line_seperator
    def get_heads(self, md_path, nlines):
        """
        get n lines from file @md_path and translate it, relocate the image
        accordingly
        """
        if nlines <= 0:
            return None
        if not os.path.isabs(md_path):
		raise NameError('Unsupport')

        rel_path = os.path.relpath(os.path.dirname(md_path), self.curr_path)

        md_src = ""
	""" 
	This is our current approach, a better method needs match the indention
	depth for last few lines, so we not encounter any sudden break
	"""
        with open(md_path) as f:
            for i in range(nlines):
                md_src += f.readline()
            f.close()
	md_src = md_src.decode('utf-8')
        (html, toc, meta) = build.convert_markdown(md_src)

	tree = etree.fromstring(u'<html>'+html+u'</html>')

	title = tree.xpath("//h1")
	if len(title) > 1:
		raise NameError("Multiple titles")
	title = title[0].text

	"""Now we relocate the images"""
	img_list = tree.xpath("//img")

	for img in img_list:
	    img_src = img.attrib['src']
	    """mkblogs create a folder for each md file, so it just adds ../ to
	    the image the file points to.

	    So we have to compute the relative path for current dir
	    """
	    if os.path.isabs(img_src):
		raise NameError('Abslute path is not supported')
	    else:
		img_src = os.path.join(rel_path, img_src)
		
	    img.attrib['src'] = img_src

        #TODO: add a readmore in the text
	return (title, ContentParser.__remove__html_tag(\
			etree.tostring(tree, encoding='utf-8')))
    @staticmethod
    def __remove__html_tag(string):
	""" remove the <html> </html> tags at head and tail """

	if string.startswith('<html>'):
	    string = string[6:]
	if string.endswith('</html>'):
	    string = string[:-7]
	return string

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
