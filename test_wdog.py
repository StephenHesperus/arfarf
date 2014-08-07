import argparse
from argparse import Namespace
import os
import sys
from io import StringIO
import subprocess
import signal
import unittest
from unittest.mock import mock_open, patch, sentinel, MagicMock

import watchdog.events
from watchdog.observers import Observer
from watchdog.observers.api import ObservedWatch

import wdconfig
from wdog import Dog, WDConfigParser, AutoRunTrick


class DogTestCase(unittest.TestCase):

    def setUp(self):
        m = mock_open(
            read_data=(
                '\n'
                '# comment line\n'
                '!not_supported\n'
                "\#hash\n"
                "\!bang!\n"
                "trailing\ \n"
                '*.py[cod]\n'
                '__pycache__/\n'
            )
        )
        self.patterns = ["\#hash", "\!bang!", "trailing\ ",
                         '*.py[cod]', '__pycache__/']
        self.patcher = patch('builtins.open', m, create=True)
        self.gitignore_mock = self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    # @unittest.expectedFailure
    def test_Dog_constructor(self):
        """Test Dog can use keywords and omit default values."""
        from wdog import Dog as dog
        try:
            dog('echo hello', ['*.py'], ['*~'], False, '.', True, True)
            dog('echo hello', ['*.py'], use_gitignore=True)
            dog(patterns=['*.py'], command='echo hello', use_gitignore=True)
            dog('echo hello')
        except:
            self.fail(__doc__)

    def test_Dog_constructor_args_default_value(self):
        """
        Dog constructor args default values:
        command: None, default log command is then provided
        patterns: None, Trick class default
        ignore_patterns: None, Trick class default
        ignore_directories: False, catches all events
        path: os.curdir, '.'
        recursive: True, catches all events
        use_gitignore: False, not all people use git, I do ,though
        """
        from wdog import Dog as dog
        try:
            d = dog()
        except:
            self.fail('Dog should be able to call without args.')
        log = 'echo ${event_object} ${event_src_path} is ${event_type}${if_moved}'
        expected = (log, None, None, False, '.', True, False)
        self.assertEqual(d.key, expected)


    def test_watch_info_property(self):
        dog = Dog(command='echo hello')
        winfo = dog.watch_info
        self.assertEqual(winfo, ('.', True))

        dog = Dog(command='echo hello', path='/dummy/path', recursive=False)
        winfo = dog.watch_info
        self.assertEqual(winfo, ('/dummy/path', False))

    def test__parse_gitignore(self):
        dog = Dog(command='echo hello')
        result = dog._parse_gitignore()
        self.gitignore_mock.assert_called_once_with(
            os.path.join(os.getcwd(), '.gitignore')
        )
        self.assertEqual(self.patterns, result)

    def test_create_handler(self):
        import watchdog.events

        monitored_path = 'monitored/path'
        dog = Dog(command='echo hello', patterns=['*.py'],
                  ignore_patterns=['more_ipattern'], use_gitignore=True,
                  path=monitored_path, recursive=True, ignore_directories=True)
        MockClass = MagicMock()
        handler = dog.create_handler(MockClass)
        ignores = [os.path.join(monitored_path, p) for p in self.patterns] + \
                  [os.path.join(monitored_path, 'more_ipattern')]
        MockClass.assert_called_once_with(
            command='echo hello',
            patterns=['monitored/path/*.py'],
            ignore_patterns=ignores,
            ignore_directories=True
        )


class WDConfigParserTestCase(unittest.TestCase):

    def setUp(self):
        from wdog import Dog as dog
        dogs_mock = (
            dog(command='echo dog1', path='.', recursive=True,
                use_gitignore=True),
            dog(command='echo dog2', path='.', recursive=True,
                use_gitignore=True),
            dog(command='echo dog3', path='..', recursive=True),
            dog(command='echo dog4', path='.', recursive=False),
        )
        self.patcher = patch('wdconfig.dogs', return_value=dogs_mock)
        d_m = self.patcher.start()
        self.dogs = d_m()
        self.parser = WDConfigParser(self.dogs)
        self.HandlerClass = MagicMock()
        self.HandlerClass.side_effect = [sentinel.a, sentinel.b,
                                         sentinel.c, sentinel.d] * 2

    def tearDown(self):
        self.patcher.stop()

    def test_schedule_with(self):
        # This provides more readable traceback message for ObservedWatch.
        def ow_repr(self):
            return str((self.path, self.is_recursive))
        setattr(ObservedWatch, '__repr__', ow_repr)
        observer = Observer()
        result = self.parser.schedule_with(observer, self.HandlerClass)
        # expected
        handlers = []
        for dog in self.dogs:
            handler = dog.create_handler(self.HandlerClass)
            handlers.append(handler)
        watches = []
        for dog in self.dogs:
            watch = ObservedWatch(*dog.watch_info)
            watches.append(watch)
        handler_for_watch = {
            watches[0]: set([handlers[0], handlers[1]]),
            watches[2]: set([handlers[2]]),
            watches[3]: set([handlers[3]]),
        }

        self.maxDiff = None
        # self.fail((result, handler_for_watch))
        self.assertEqual(result, handler_for_watch)

    def test__parse_gitignore_called_at_most_once_in_create_handler(self):
        with patch.object(Dog, '_parse_gitignore') as mg:
            observer = Observer()
            self.parser.schedule_with(observer, self.HandlerClass)
            self.assertIs(Dog._parse_gitignore, mg)
        mg.assert_called_once_with()


class AutoRunTrickTestCase(unittest.TestCase):
    """
    The only difference between AutoRunTrick and AutoRestartTrick is the way
    they handle command parsing and execution. So the this test case only
    focus on it.
    """

    def test_command_is_positional_arg(self):
        with self.assertRaises(TypeError):
            handler = AutoRunTrick()
        try:
            handler = AutoRunTrick('echo hello')
        except:
            self.fail('"command" should be a positional argument.')

    def test_command_property(self):
        handler = AutoRunTrick(command='echo hello')
        self.assertEqual('echo hello', handler.command)

    def test_command_default(self):
        handler = AutoRunTrick(command='')
        expected = ('echo ${event_object} ${event_src_path} is '
                    '${event_type}${if_moved}')
        self.assertEqual(expected, handler.command)

        handler = AutoRunTrick(command='echo hello')
        self.assertEqual('echo hello', handler.command)

    def test_command_default_substitution(self):
        from string import Template
        from watchdog.events import FileCreatedEvent, DirMovedEvent

        handler = AutoRunTrick(command='')
        path = '/source/path'
        event = FileCreatedEvent(path)
        command = handler._substitute_command(event)
        t = Template('echo ${event_object} ${event_src_path} is '
                     '${event_type}${if_moved}')
        created = {'event_object': 'file', 'event_src_path': path,
                   'event_type': 'created', 'if_moved': ''}
        expected = t.safe_substitute(**created)
        self.assertEqual(expected, command)

        # directory moved event
        dest = '/dest/path'
        event = DirMovedEvent(path, dest)
        command = handler._substitute_command(event)
        moved = {'event_object': 'directory', 'event_src_path': path,
                   'event_type': 'moved', 'if_moved': ' to "%s"' % dest}
        expected = t.safe_substitute(**moved)
        self.assertEqual(expected, command)

    def test_command_shell_environment_variables(self):
        from string import Template
        from watchdog.events import DirMovedEvent

        command = 'echo ${event_dest_path}'
        handler = AutoRunTrick(command)
        path = '/source/path'
        dest = '/dest/path'
        event = DirMovedEvent(path, dest)
        command = handler._substitute_command(event)
        context = {'event_dest_path': dest}
        expected = Template(command).safe_substitute(**context)
        self.assertEqual(expected, command)

    def test_equality(self):
        handler1 = AutoRunTrick(command='echo hello')
        handler2 = AutoRunTrick(command='echo hello')

        self.assertEqual(handler1, handler2)

    def test_hashable(self):
        import collections
        handler = AutoRunTrick(command='echo hello')
        self.assertTrue(isinstance(handler, collections.Hashable))

    def test___repr__(self):
        handler = AutoRunTrick(command='echo hello')
        repr_str = ('<AutoRunTrick: command={}, patterns={}, ignore_patterns={},'
                'ignore_directories={}>').format(*handler.key)
        self.assertEqual(repr_str, repr(handler))

    def test_start(self):
        handler = AutoRunTrick('echo hello')
        handler.start(out=subprocess.PIPE)
        outs, errs = handler._process.communicate()
        self.assertEqual('hello\n', outs.decode())

    def test_start_with_event(self):
        from watchdog.events import DirMovedEvent

        handler = AutoRunTrick('')
        event = DirMovedEvent('/source/path', '/dest/path')
        handler.start(event=event, out=subprocess.PIPE)
        outs, errs = handler._process.communicate()
        expected = b'directory /source/path is moved to /dest/path\n'
        self.assertEqual(expected, outs)

    def test_start_with_command_default_and_no_event(self):
        from watchdog.events import DirMovedEvent

        handler = AutoRunTrick('')
        handler.start(out=subprocess.PIPE)
        outs, errs = handler._process.communicate()
        self.assertEqual('', outs.decode())

    def test_stop(self):
        handler = AutoRunTrick('echo hello')
        handler.start()
        handler.stop()
        self.assertIs(handler._process, None)

    def test_on_any_event(self):
        from watchdog.events import DirMovedEvent

        handler = AutoRunTrick('')
        event = DirMovedEvent('/source/path', '/dest/path')
        handler.on_any_event(event, subprocess.PIPE)
        outs, errs = handler._process.communicate()
        expected = b'directory /source/path is moved to /dest/path\n'
        self.assertEqual(outs, expected)


class MainEntryTestCase(unittest.TestCase):

    def setUp(self):
        import wdog
        self.parser = wdog._create_main_argparser()

    def test__create_main_argparser_without_args(self):
        result = self.parser.parse_args([])
        self.assertEqual(Namespace(config=None, gitignore=None), result)

    def test__create_main_argparser_with_config_option(self):
        lresult = self.parser.parse_args(['--config-file', 'dogs.py'])
        sresult = self.parser.parse_args(['-c', 'dogs.py'])
        self.assertEqual(lresult, sresult)
        self.assertEqual(lresult, Namespace(config='dogs.py', gitignore=None))

    def test__create_main_argparser_with_gitignore_option(self):
        lresult = self.parser.parse_args(['--gitignore', '.gitignore'])
        sresult = self.parser.parse_args(['-g', '.gitignore'])
        self.assertEqual(lresult, sresult)
        self.assertEqual(lresult,
                         Namespace(config=None, gitignore='.gitignore'))

    def test__create_main_argparser_with_unknown_option(self):
        def error(self, *args, **kwargs):
            raise SystemExit

        with patch.object(argparse.ArgumentParser, 'error', new=error) as m:
            self.assertIs(argparse.ArgumentParser.error, m)
            args = ['--unknown-option', 'unknown-option']
            with self.assertRaises(SystemExit):
                self.parser.parse_args(args)


@unittest.skip('WIP')
class FunctionalTestCase(unittest.TestCase):

    def test_wdog_script_execution(self):
        from tempfile import NamedTemporaryFile, TemporaryDirectory

        # Entry temporary directory.
        td = TemporaryDirectory()
        oldwd = os.getcwd()
        os.chdir(td.name)

        # Redirect command output to temporary file.
        with NamedTemporaryFile(mode='w+b') as t:
            # Fixtures set up.
            wdogpy = os.path.join(oldwd, 'wdog.py')
            fixture_wdconfigpy = os.path.join(oldwd, 'fixture_wdconfig.py')
            fixture_gitignore = os.path.join(oldwd, 'fixture_gitignore')

            cmd = 'python3 {} -c {} -g {} > {}'.format(wdogpy,
                                                       fixture_wdconfigpy,
                                                       fixture_gitignore,
                                                       t.name)

            p = subprocess.Popen(cmd, shell=True, start_new_session=True)

            def sh(command):
                subprocess.call(command, shell=True)

            # Test file system events.
            # file events
            # file created event
            sh('touch dummy')
            # file modified event
            # file moved event
            # file deleted event
            # directory events
            # directory created event
            # directory modified event
            # directory moved event
            # directory deleted event
            # ignored file system events

            try:
                # Wait for the redirect operation to finish.
                p.wait(1)
            except subprocess.TimeoutExpired:
                os.killpg(os.getpgid(p.pid), signal.SIGINT)

            t.seek(0)
            result = set(t.read().split(b'\n'))
            expected = set(b'hello world\nnice to meet you\n'.split(b'\n'))
            self.fail(result)
            self.assertEqual(result, expected)

        # Exit temporary directory.
        os.chdir(oldwd)
        td.cleanup()


class MiscellaneousTestCase(unittest.TestCase):

    def test_fnmatch_func(self):
        from fnmatch import fnmatch
        from os.path import join

        def match(name, pattern):
            self.assertTrue(fnmatch(name, pattern))

        def notmatch(name, pattern):
            self.assertFalse(fnmatch(name, pattern))

        # relative to os.curdir
        match('dummy', 'dummy')
        notmatch('./dummy', 'dummy')
        match('./dummy', join('.', 'dummy'))

        # relative to 'relative'
        match('relative/path', 'relative/path')
        notmatch('relative/path', 'path')
        match('relative/path', join('relative', 'path'))

        # absolute path
        match('/absolute/path', '/absolute/path')
        notmatch('/absolute/path', 'absolute/path')
        notmatch('/absolute/path', 'path')
        match('/absolute/path', join('/absolute', 'path'))

        # directory
        match('./directory/', './directory/')
        notmatch('./directory/', './directory') # dir matching file
        notmatch('./directory', './directory/')
        match(join('./directory', ''), './directory/')
        match(join('./directory/', ''), './directory/')
        match(join('/abs/dir', ''), join('/abs', 'dir/'))
