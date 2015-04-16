import os, operator
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
    with open(path, 'w') as f:
        f.write("#{}\n".format(title))
        f.write("\n")
        for (name, blog_path, build_time) in sorted_inds:
            f.write("*  [{0}]({1})\n".format(name, blog_path))
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
            f.write("*  [{0}]({1})\n".format(name, os.path.relpath(index_path, path)))
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
