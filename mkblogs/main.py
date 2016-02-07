#!/usr/bin/env python2
# coding: utf-8
from __future__ import print_function

import logging
import sys

from mkblogs import __version__
from mkblogs.build import build
from mkblogs.config import load_config
from mkblogs.exceptions import MkDocsException
from mkblogs.gh_deploy import gh_deploy
from mkblogs.new import new
from mkblogs.serve import serve


def configure_logging(options):
    '''When a --verbose flag is passed, increase the verbosity of mkblogs'''
    logger = logging.getLogger('mkblogs')
    logger.addHandler(logging.StreamHandler())
    if 'verbose' in options:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.WARNING)


def arg_to_option(arg):
    """
    Convert command line arguments into two-tuples of config key/value pairs.
    """
    arg = arg.lstrip('--')
    option = True
    if '=' in arg:
        arg, option = arg.split('=', 1)
    return (arg.replace('-', '_'), option)


def main(cmd, args, options=None):
    """
    Build the documentation, and optionally start the devserver.
    """
    configure_logging(options)
    clean_site_dir = 'clean' in options
    if cmd == 'serve':
        config = load_config(options=options)
        serve(config, options=options)
    elif cmd == 'build':
        config = load_config(options=options)
        build(config, clean_site_dir=clean_site_dir)
    elif cmd == 'json':
        config = load_config(options=options)
        build(config, dump_json=True, clean_site_dir=clean_site_dir)
    elif cmd == 'gh-deploy':
        config = load_config(options=options)
        build(config, clean_site_dir=clean_site_dir)
        gh_deploy(config)
    elif cmd == 'new':
        new(args, options)
    else:
        print('MkDocs (version {0})'.format(__version__))
        print('mkblogs [help|new|build|serve|gh-deploy|json] {options}')


def run_main():
    """
    Invokes main() with the contents of sys.argv

    This is a separate function so it can be invoked
    by a setuptools console_script.
    """
    cmd = sys.argv[1] if len(sys.argv) >= 2 else None
    opts = [arg_to_option(arg) for arg in sys.argv[2:] if arg.startswith('--')]
    try:
        main(cmd, args=sys.argv[2:], options=dict(opts))
    except MkDocsException as e:
        print(e.args[0], file=sys.stderr)


if __name__ == '__main__':
    run_main()
