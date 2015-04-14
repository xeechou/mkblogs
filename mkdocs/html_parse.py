#!/usr/bin/env python2.7
from lxml import etree
import os
from mkdocs import build as builder
import logging
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
        (html, toc, meta) = builder.convert_markdown(md_src)

	tree = etree.fromstring(u'<html>'+html+u'</html>')

	title = tree.xpath("//h1")
	if len(title) > 1:
		raise NameError("Multiple titles")
	title = title[0].text

	"""Now we relocate the images"""
	img_list = tree.xpath("//img")

	for img in img_list:
	    img_src = img.attrib['src']
	    """mkdocs create a folder for each md file, so it just adds ../ to
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
    md_path = 'test/path1/BigCLAM.md'
    content = ContentParser.get_heads(os.path.abspath(md_path), os.getcwd(), 20)
    print content[1]
