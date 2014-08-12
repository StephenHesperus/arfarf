#!/usr/bin/env python3

"""
A script to run commands upon file system events.

Usage
=====
Recommanded: Run this script under your project root, this is mandatory if you
set the ``use_gitignore`` option of a dog in the wdconfig.py file.
"""


import argparse
import os


def _create_main_argparser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config-file', '-c', dest='config',
                        help=('specify a config file to provide dogs,'
                              'the format should be the same as wdconfig.py'))
    parser.add_argument('--gitignore', '-g', dest='gitignore',
                        help=('specify a .gitignore file to provide patterns'
                              'to ignore'))
    return parser


def _apply_main_args(args):
    if args.config is not None:
        import sys
        import importlib

        mpath = os.path.dirname(args.config)
        sys.path.insert(0, mpath)
        mbase = os.path.basename(args.config)
        mname = os.path.splitext(mbase)[0]
        wdconfig = importlib.import_module(mname)
    else:
        import wdconfig

    if args.gitignore is not None:
        gitignore_path = os.path.join(os.curdir, args.gitignore)
        from dog import Dog

        Dog.set_gitignore_path(gitignore_path)

    return wdconfig


def main():
    """Script entry point."""
    from watchdog.observers.polling import PollingObserver
    from parser import WDConfigParser
    from tricks import AutoRunTrick

    parser = _create_main_argparser()
    args = parser.parse_args()
    wdconfig = _apply_main_args(args)

    # The reason to use PollingObserver() is it's os-independent. And it's
    # more reliable.
    observer = PollingObserver()

    parser = WDConfigParser(wdconfig)
    handler_for_watch = parser.schedule_with(observer, AutoRunTrick)
    handlers = set.union(*tuple(handler_for_watch.values()))

    for handler in handlers:
        handler.start()
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
    for handler in handlers:
        handler.stop()


if __name__ == '__main__':
    main()
