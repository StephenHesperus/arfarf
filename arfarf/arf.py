#!/usr/bin/env python3

import argparse
import os
import sys
import time


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _create_main_argparser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config-file', '-c', dest='config',
                        help=('specify a config file to provide dogs, the '
                              'format should be the same as arfarfconfig.py'))
    parser.add_argument('--gitignore', '-g', dest='gitignore',
                        help=('specify a .gitignore file to provide patterns'
                              'to ignore'))
    parser.add_argument('--create-config', '-t', dest='template',
                        action='store_true',
                        help=('create the arfarfconfig.py config file'
                              'using the default template'))
    return parser


def _apply_main_args(args):
    if args.template:
        import shutil

        if not os.path.exists('./arfarfconfig.py'):
            shutil.copy(os.path.join(BASE_DIR, 'arfarfconfig_template'),
                        './arfarfconfig.py')
            return
        else:
            sys.exit('arfarfconfig.py already exists!')

    configm = None
    if args.config is not None:
        import importlib

        mpath = os.path.dirname(args.config)
        sys.path.append(mpath)
        mbase = os.path.basename(args.config)
        mname = os.path.splitext(mbase)[0]
        try:
            configm = importlib.import_module(mname)
        except ImportError as e:
            sys.exit(e.msg)
    else:
        try:
            import arfarfconfig
        except ImportError as e:
            sys.exit(e.msg)
        else:
            configm = arfarfconfig

    if args.gitignore is not None:
        gitignore_path = os.path.join(os.curdir, args.gitignore)
        if os.path.isfile(gitignore_path):
            from .dog import Dog
            Dog.set_gitignore_path(gitignore_path)
        else:
            sys.exit("File not found: '%s'" % gitignore_path)

    return configm


def main():
    """Script entry point."""
    from watchdog.observers.polling import PollingObserver
    from parser import WDConfigParser
    from tricks import AutoRunTrick

    parser = _create_main_argparser()
    args = parser.parse_args()
    configm = _apply_main_args(args)

    # The reason to use PollingObserver() is it's os-independent. And it's
    # more reliable.
    observer = PollingObserver()

    parser = WDConfigParser(configm)
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
