#!/usr/bin/env python2
import os, re, time
import operator
import markdown

from html_parse import ContentParser

omit_path=['index.md', 'img']    #these are the initial omited path
n_newsest_blog = 5

dot_ignore = ".ignore"
#TODO: change root path to a relative path, where we invoke mkblogs build
class ScanKeep:
    def __init__(self, topn, config):
        self.topn = topn or config.get('top_n_blogs')
        self.config = config
        self.cata_list = cata_list
def scan_dir(config, rootdir, n=5):
    """
    @rootdir is a relative path where stores all the blogs.
    If you are under docs/, rootdir should be "."
    """
    global n_newsest_blog
    n_newsest_blog = n

    basename = os.path.basename(rootpath)
    #XXX: need more detailed code
    if basename != 'docs':
        raise NameError('The root directory should be \'docs\'')

    return recursive_scan(rootdir, genindex=False)

"""
    newest_path = recursive_scan(rootpath, genindex=False)
    indexmd = open('index.md','w')  #coz we are out of "docs/", use 'index.md'
                                    #directly
    write_top_indexmd(os.path.join(rootpath, 'index.md'), newest_path)
    #now, we should generate the top index.md
"""

def write_top_indexmd(indexmd_path, newest_path):
    assert os.path.isfile(indexmd_path) || not os.path.exists(indexmd_path)

    indexmd_dir = os.path.dirname(indexmd_path)
    parser = ContentParser(indexmd_dir)

    head_list = []
    for path in newest_path:
	head_list.append(parser.get_heads(path, 20))
    html  = parser.merge_htmls(head_list) 

    with open(indexmd_path, 'w') as f:
	f.write(html)
	f.close()

def write_indexmd(fp, files_path):
    #TODO
    pass

def add_top_n(newest_paths, to_add, n):
    to_sort = newest_paths.extend(to_add)
    return sorted(to_sort, key=operator.itemgetter(1), \
            reverse=True)[:n]

def read_ignore(ignore_file):
    ignored_list = []
    if not os.path.isfile(ignored_files):
        return ignored_list
    else:
        with open(ignored_file) as f:
            for line in f:
                ignored_files.append(line)
            f.close()
        return ignored_files

def recursive_scan(this_path, genindex=True):
    """
    maintain a mewest path and a tree of docs
    @this_path is '.', but we are not in current_path, so @this_path may look
    like docs/BigCLAM

    return newest path
    """
    global omit_path
    newest_path = []
    local_path = {}

    paths = os.listdir(this_path)
    ignored_files = read_ignore(os.path.join(this_path, dot_ignore))
    for f in paths:
        #locally ignored
        if f == dot_ignore:
            continue
        if f in ignored_files:
            continue
        #globally ignored,
        abs_path = os.path.join(this_path, f)
        if abs_path in omit_path:
            continue

        #XXX: @abs_path is not abs path at all, it starts at 'docs'
        if os.path.isfile(abs_path):
            pair = (abs_path, os.path.getatime(abs_path))
            local_path[abs_path] = pair[1]
            add_top_n(newest_path, [pair])
            pagelist.append(abs_path)

        elif os.path.isdir(abs_path):
            sub_newest_path = recursive_scan(abs_path)
            add_top_n(newest_path, sub_newest_path)
        else:
            continue

        #now, we should generate a index.md for this dir
    if genindex == True:
        index_md = open(os.path.json(parent_path, 'index.md'), 'w')
        write_indexmd(index_md, local_path)
        index_md.close()

    return newest_path
