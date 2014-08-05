import os
import subprocess
import signal
import unittest
from unittest.mock import mock_open, patch, sentinel

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

    def test_Dog_constructor(self):
        """Test Dog can use keywords and omit default values."""
        from wdog import Dog as dog
        try:
            dog('echo hello', ['*.py'], [], False, '.', True, True)
            dog('echo hello', ['*.py'], use_gitignore=True)
            dog(patterns=['*.py'], command='echo hello', use_gitignore=True)
            dog('echo hello')
        except:
            self.fail(__doc__)

        with self.assertRaises(Exception):
            dog()

    def test__parse_gitignore(self):
        dog = Dog(command='echo hello')
        result = dog._parse_gitignore()
        self.gitignore_mock.assert_called_once_with(
            os.path.join(os.getcwd(), '.gitignore')
        )
        self.assertEqual(self.patterns, result)

    def test_create_handler(self):
        import watchdog.events
        dog = Dog(command='echo hello', patterns=['*.py'],
                  ignore_patterns=['more_ipattern'], use_gitignore=True,
                  path='.', recursive=True, ignore_directories=True)
        with patch('watchdog.events.PatternMatchingEventHandler') as MockClass:
            handler = dog.create_handler(
                watchdog.events.PatternMatchingEventHandler
            )
            self.assertIs(watchdog.events.PatternMatchingEventHandler,
                          MockClass)
            MockClass.assert_called_once_with(
                command='echo hello',
                patterns=['*.py'],
                ignore_patterns=['more_ipattern'] + self.patterns,
                ignore_directories=True
            )

    def test_watch_info_property(self):
        dog = Dog(command='echo hello')
        winfo = dog.watch_info
        self.assertEqual(winfo, ('.', True))

        dog = Dog(command='echo hello', path='/dummy/path', recursive=False)
        winfo = dog.watch_info
        self.assertEqual(winfo, ('/dummy/path', False))


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
        self.hpatcher = patch('watchdog.events.PatternMatchingEventHandler')
        handler = self.hpatcher.start()
        # make each handler created is different from the other
        handler.side_effect = [sentinel.a, sentinel.b, sentinel.c,
                               sentinel.d] * 2
        self.HandlerClass = handler

    def tearDown(self):
        self.patcher.stop()
        self.hpatcher.stop()

    def test_schedule_with(self):
        # This provides more readable traceback message for ObservedWatch.
        def ow_repr(self):
            return str((self.path, self.is_recursive))
        setattr(ObservedWatch, '__repr__', ow_repr)
        observer = Observer()
        result = self.parser.schedule_with(
            observer,
            watchdog.events.PatternMatchingEventHandler
        )
        # expected
        handlers = []
        for dog in self.dogs:
            handler = dog.create_handler(
                watchdog.events.PatternMatchingEventHandler
            )
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
        # self.fail(result)
        # self.fail(handler_for_watch)
        self.assertEqual(result, handler_for_watch)

    def test__parse_gitignore_called_at_most_once_in_create_handler(self):
        with patch.object(Dog, '_parse_gitignore') as mg:
            observer = Observer()
            self.parser.schedule_with(
                observer,
                watchdog.events.PatternMatchingEventHandler
            )
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
        handler.start(subprocess.PIPE)
        outs, errs = handler._process.communicate()
        self.assertEqual('hello\n', outs.decode())

    def test_start_with_event(self):
        from watchdog.events import DirMovedEvent

        handler = AutoRunTrick('')
        event = DirMovedEvent('/source/path', '/dest/path')
        handler.start(subprocess.PIPE, event)
        outs, errs = handler._process.communicate()
        expected = 'directory /source/path is moved to /dest/path\n'
        self.assertEqual(expected, outs.decode())

    def test_start_with_command_default_and_no_event(self):
        from watchdog.events import DirMovedEvent

        handler = AutoRunTrick('')
        handler.start(subprocess.PIPE)
        outs, errs = handler._process.communicate()
        self.assertEqual('', outs.decode())

    def test_stop(self):
        handler = AutoRunTrick('echo hello')
        handler.start(subprocess.PIPE)
        handler.stop()
        self.assertIs(handler._process, None)


class MainEntryTestCase(unittest.TestCase):

    def setUp(self):
        import wdog
        self.parser = wdog._create_main_argparser()

    @unittest.skip('WIP')
    def test_main_with_no_arg(self):
        import multiprocessing
        import wdog

        p = multiprocessing.Process(target=wdog.main)
        p.start()
        try:
            # Let wdog.main() run for 0.01 sec.
            p.join(0.01)
            p.terminate()
        except:
            self.fail('wdog.main() should work without args.')

    @unittest.skip('WIP')
    def test_main_with_config_file_option(self):
        import multiprocessing
        import wdog

        c = ['-c', 'hello.py']
        p = multiprocessing.Process(target=wdog.main, args=(c,))
        p.start()
        try:
            # Let wdog.main() run for 0.1 sec.
            p.join(0.1)
            p.terminate()
        except:
            self.fail('wdog.main() should work with --config-file/-c option.')

    @unittest.skip('WIP')
    def test_main_with_gitignore_option(self):
        import multiprocessing
        import wdog

        c = ['-g', '.gitignore']
        p = multiprocessing.Process(target=wdog.main, args=(c,))
        p.start()
        try:
            # Let wdog.main() run for 0.1 sec.
            p.join(0.1)
            p.terminate()
        except:
            self.fail('wdog.main() should work with --gitignore/-g option.')

    @unittest.skip('WIP')
    def test_main_with_unknown_option(self):
        import multiprocessing
        import wdog

        c = ['--unknown-option', 'unknown-option']
        p = multiprocessing.Process(target=wdog.main, args=(c,))
        p.start()
        # wait for 1 sec
        for _ in range(10):
            p.join(0.1)
            if not p.is_alive():
                self.assertEqual(p.exitcode,
                                 2, # SystemExit 2 when unknown option
                                 'wdog.main() should not work '
                                 'with --unknown-optiong option.')
                break
        else:
            p.terminate()
            self.fail('wdog.main() should not work '
                      'with --unknown-optiong option.')

    def test__create_main_argparser_without_args(self):
        try:
            self.parser.parse_args([])
        except SystemExit:
            self.fail('_create_main_argparser() should work without args.')

    def test__create_main_argparser_config_option(self):
        try:
            self.parser.parse_args(['--config-file', 'dogs.py'])
            self.parser.parse_args(['-c', 'dogs.py'])
        except SystemExit:
            self.fail('_create_main_argparser() should work '
                      'with --config-file/-c option.')

    def test__create_main_argparser_gitignore_option(self):
        try:
            self.parser.parse_args(['--gitignore', '.gitignore'])
            self.parser.parse_args(['-g', '.gitignore'])
        except SystemExit:
            self.fail('_create_main_argparser() should work '
                      'with --gitignore/-g option.')

    def test__create_main_argparser_with_unknown_option(self):
        with self.assertRaises(SystemExit):
            self.parser.parse_args(['--unknown-option', 'unknown-option'])


class FunctionalTestCase(unittest.TestCase):

    @unittest.skip('WIP')
    def test_wdog_script_execution(self):
        from tempfile import NamedTemporaryFile, TemporaryDirectory

        # Entry temporary directory.
        # td = TemporaryDirectory()
        # pwd = os.getcwd()
        # os.chdir(td.name)

        with NamedTemporaryFile(mode='w+b') as t:
            p = subprocess.Popen('python3 wdog.py > %s' % t.name, shell=True,
                                 start_new_session=True)
            try:
                # Wait for the write operation to finish.
                p.wait(1)
            except subprocess.TimeoutExpired:
                os.killpg(os.getpgid(p.pid), signal.SIGINT)

            t.seek(0)
            self.assertEqual(t.read(), b'hello world\n')

        # Exit temporary directory.
        # os.chdir(pwd)
        # td.cleanup()
