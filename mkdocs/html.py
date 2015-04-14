from mkdocs import utils, nav

def get_located_path(file_path):
    """
    get a file's located dir from its abs_path file_name. If we only get a file_name
    provided, the result will be ''
    """
    return os.path.basename(os.path.dirname(file_path))

def write_index(path, indices, title=None):
    """
    write @indices to @path, generate title if not provided
    """
    if not title:
        dirname = get_located_path(path)
        if dirname:
            title = nav.filename_to_title(dirname)
        else:
            title = 'Index'
    with open(path, 'w') as f:
        f.write("#{}\n".format(title))
        f.write("\n")
        for (name, blog_path) in indices:
            f.write("[{0}]({1})".format(name, os.path.relpath(blog_path, path)))
        f.close()

def write_catalog(path, catalist):
    """
    write the top catalog page for blogs according to catalist,
    catalist is list of dirnames, in mkdocs's scenario, it will treat dirname as
    actual file, and transfer to 'dirname/index.md', which points to exact
    location of the index file. If using our senario, we will treat it as dir,
    then it points to dirname.
    """
    with open(path, 'w') as f:
        for (name, index_path) in catalist:
            f.write("[{0}]({1})".format(name, os.path.relpath(index_path, path)))
        f.close()

