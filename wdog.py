#!/usr/bin/env python3

"""
A script to run commands upon file system events.

Usage
=====
Recommanded: Run this script under your project root, this is mandatory if you
set the ``use_gitignore`` option of a dog in the wdconfig.py file.
"""


import os
import signal
import subprocess
import time
import argparse

from collections import defaultdict
from string import Template

from pathtools.patterns import match_any_paths
from watchdog.tricks import Trick
from watchdog.utils import unicode_paths
from watchdog.events import EVENT_TYPE_CREATED, EVENT_TYPE_MODIFIED
from watchdog.events import EVENT_TYPE_MOVED, EVENT_TYPE_DELETED


class WDConfigParser(object):
    """
    Parser for wdconfig.py file.
    """

    def __init__(self, wdconfig_module):
        self._dogs = wdconfig_module.dogs
        self._use_gitignore_default = wdconfig_module.use_gitignore_default
        self._wdconfig = wdconfig_module

    def _set_use_gitignore_default(self):
        from dog import Dog
        Dog._use_gitignore_default = self._use_gitignore_default

    def schedule_with(self, observer, cls):
        self._set_use_gitignore_default()

        handler_for_watch = defaultdict(set)
        for dog in self._dogs:
            handler = dog.create_handler(cls)
            watch = observer.schedule(handler, *dog.watch_info)
            handler_for_watch[watch].add(handler)
        handler_for_watch = dict(handler_for_watch)

        return handler_for_watch


class AutoRunTrick(Trick):
    """
    A variant of AutoRestartTrick.
    When called without arguments, it's the same as a logger of file system
    events.
    """

    _command_default = ('echo ${event_object} ${event_src_path} is '
                        '${event_type}${if_moved}')

    def __init__(self, command=None, patterns=None, ignore_patterns=None,
                 ignore_directories=False, stop_signal=signal.SIGINT,
                 kill_after=10):
        # Matches Trick.__init__() signature.
        super().__init__(patterns, ignore_patterns, ignore_directories)
        self._command = command if command is not None \
                        else type(self)._command_default
        self._stop_signal = stop_signal
        self._kill_after = kill_after
        self._process = None

    def __eq__(self, value):
        return isinstance(value, self.__class__) and self.key == value.key

    def __ne__(self, value):
        return not self.__eq__(value)

    def __hash__(self):
        return hash(self.key)

    def __repr__(self):
        repr_str = ('<AutoRunTrick: command={}, patterns={}, ignore_patterns={},'
                'ignore_directories={}>').format(*self.key)
        return repr_str

    def _substitute_command(self, event):
        if event is None:
            c = self._command if self._command != type(self)._command_default \
                else ''
            return c

        dest = event.dest_path if hasattr(event, 'dest_path') else ''
        if_moved = ' to "%s"' % dest if dest else ''
        context = {
            'event_object': 'directory' if event.is_directory else 'file',
            'event_src_path': event.src_path,
            'event_type': event.event_type,
            'event_dest_path': dest,
            'if_moved': if_moved,
        }
        command = Template(self._command).safe_substitute(**context)
        return command

    @property
    def command(self):
        return self._command

    def start(self, event=None, out=None,):
        command = self._substitute_command(event)
        self._process = subprocess.Popen(command, shell=True,
                                         start_new_session=True, stdout=out)

    def stop(self):
        if self._process is None:
            return
        try:
            os.killpg(os.getpgid(self._process.pid), self._stop_signal)
        except OSError:
            # Process is already gone.
            pass
        else:
            kill_time = time.time() + self._kill_after
            while time.time() < kill_time:
                if self._process.poll() is not None:
                    break
                time.sleep(0.25)
            else:
                try:
                    os.killpg(os.getpgid(self._process.pid, signal.SIGKILL))
                except OSError:
                    pass
        self._process = None

    def on_any_event(self, event, out=None):
        self.stop()
        self.start(event=event, out=out)

    @property
    def key(self):
        if self.patterns is None:
            patterns = None
        else:
            patterns = tuple(self.patterns)
        if self.ignore_patterns is None:
            ignore_patterns = None
        else:
            ignore_patterns = tuple(self.ignore_patterns)
        return (self.command,
                patterns, ignore_patterns,
                self.ignore_directories)

    def dispatch(self, event):
        if event.is_directory and self._ignore_directories:
            return

        paths = []
        if hasattr(event, 'dest_path'):
            if event.is_directory:
                dest_path = os.path.join(event.dest_path, '')
            else:
                dest_path = event.dest_path
            paths.append(unicode_paths.decode(dest_path))
        if event.src_path:
            if event.is_directory:
                src_path = os.path.join(event.src_path, '')
            else:
                src_path = event.src_path
            paths.append(unicode_paths.decode(src_path))

        if match_any_paths(paths,
                           included_patterns=self._patterns,
                           excluded_patterns=self._ignore_patterns,
                           case_sensitive=self.case_sensitive):
            self.on_any_event(event)
            method_map = {
                EVENT_TYPE_CREATED: self.on_created,
                EVENT_TYPE_MODIFIED: self.on_modified,
                EVENT_TYPE_MOVED: self.on_moved,
                EVENT_TYPE_DELETED: self.on_deleted,
            }
            event_type = event.event_type
            method_map[event_type](event)


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
