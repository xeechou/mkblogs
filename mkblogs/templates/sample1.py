# -*- coding: utf-8 -*-
import jinja2
from jinja2.exceptions import TemplateNotFound

if __name__=="__main__":
    theme_dir = '../themes/journal'
    loader = jinja2.FileSystemLoader(theme_dir)
    env = jinja2.Environment(loader=loader)
    template = env.get_template('base.html')
    print(template.globals)


