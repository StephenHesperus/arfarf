import argparse
from argparse import Namespace
import os
import subprocess
import unittest
from unittest.mock import mock_open, patch, sentinel, MagicMock

from watchdog.observers import Observer
from watchdog.observers.api import ObservedWatch

from bark.dog import Dog
from bark.parser import WDConfigParser
from bark.tricks import AutoRunTrick


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
        try:
            Dog('echo hello', ['*.py'], ['*~'], False, '.', True, True)
            Dog('echo hello', ['*.py'], use_gitignore=True)
            Dog(patterns=['*.py'], command='echo hello', use_gitignore=True)
            Dog('echo hello')
        except:
            self.fail(__doc__)

    def test_Dog_constructor_args_default_value(self):
        """
        Dog constructor args default values:
        command: None, subclass of FileSystemEventHandler should provide a
                 default value
        patterns: None, Trick class default
        ignore_patterns: None, Trick class default
        ignore_directories: False, catches all events
        path: os.curdir, '.'
        recursive: True, catches all events
        use_gitignore: False, not all people use git, I do ,though
        """
        try:
            d = Dog()
        except:
            self.fail('Dog should be able to call without args.')
        # log = 'echo ${event_object} ${event_src_path} is ${event_type}${if_moved}'
        expected = (None, None, None, False, '.', True, False)
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
            os.path.join(os.curdir, '.gitignore')
        )
        self.assertEqual(self.patterns, result)

    def test_create_handler(self):
        monitored_path = 'monitored/path'
        dog = Dog(command='echo hello', patterns=['*.py'],
                  ignore_patterns=['more_ipattern'], use_gitignore=True,
                  path=monitored_path, recursive=True, ignore_directories=True)
        MockClass = MagicMock()
        _ = dog.create_handler(MockClass)
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
        from bark.dog import Dog as dog
        self.dogs = (
            dog(command='echo dog1', path='.', recursive=True,
                use_gitignore=True),
            dog(command='echo dog2', path='.', recursive=True,
                use_gitignore=True),
            dog(command='echo dog3', path='..', recursive=True),
            dog(command='echo dog4', path='.', recursive=False),
        )
        self.wdmm = MagicMock()
        self.wdmm.dogs = self.dogs
        self.wdmm.use_gitignore_default = True
        self.wdmm.gitignore_path = '.gitignore'
        self.patcher = patch.dict('sys.modules', wdconfig_module=self.wdmm)
        self.patcher.start()
        import wdconfig_module
        self.parser = WDConfigParser(wdconfig_module)
        self.HandlerClass = MagicMock()
        self.HandlerClass.side_effect = [sentinel.a, sentinel.b,
                                         sentinel.c, sentinel.d] * 2
        Dog._gitignore = None

    def tearDown(self):
        self.patcher.stop()

    def test_schedule_with(self):
        # This provides more readable traceback message for ObservedWatch.
        def ow_repr(self):
            return str((self.path, self.is_recursive))
        setattr(ObservedWatch, '__repr__', ow_repr)

        # mock open so that files other than '.gitignore' raise exception
        m = mock_open(read_data='*.py[cod]\n__pycache__/\n')
        patcher = patch('builtins.open', m)
        patcher.start()

        # reset gitignore path to '.gitignore' (a file that exists)
        self.parser._gitignore_path = '.gitignore'
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
        patcher.stop()

    def test__parse_gitignore_called_at_most_once_in_create_handler(self):
        with patch.object(Dog, '_parse_gitignore') as mg:
            observer = Observer()
            self.parser.schedule_with(observer, self.HandlerClass)
            self.assertIs(Dog._parse_gitignore, mg)
        mg.assert_called_once_with()

    def test_construct_using_wdconfig_module(self):
        import wdconfig_module

        self.assertIsNotNone(self.parser._wdconfig)
        self.assertIs(self.parser._wdconfig, wdconfig_module)

    def test_can_set_Dog_use_gitignore_defaut_cls_attr(self):
        use = self.parser._use_gitignore_default # True
        self.parser._set_use_gitignore_default()
        self.assertEqual(use, Dog._use_gitignore_default)
        # newly created Dog() _use_gitignore_default is changed
        dog = Dog()
        self.assertEqual(dog._use_gitignore_default, use)
        # _use_gitignore_default of dogs in wdconfig are changed
        self.assertEqual(self.wdmm.dogs[0]._use_gitignore_default, use)

        self.wdmm.use_gitignore_default = False
        parser = WDConfigParser(self.wdmm)
        parser._set_use_gitignore_default()
        self.assertEqual(parser._use_gitignore_default,
                         Dog._use_gitignore_default)
        dog = Dog()
        self.assertEqual(dog._use_gitignore_default, False)
        self.assertEqual(self.wdmm.dogs[0]._use_gitignore_default, False)

    def test_can_set_Dog_gitignore_path_cls_attr(self):
        # self.parser._gitignore_path is '.gitignore'
        self.assertEqual(Dog._gitignore_path, './.gitignore')

        # change gitignore file path to .bzrignore
        self.wdmm.gitignore_path = '.bzrignore'
        parser = WDConfigParser(self.wdmm)
        parser._set_gitignore_path()
        self.assertEqual('./.bzrignore', Dog._gitignore_path)
        dog = Dog()
        self.assertEqual(dog._gitignore_path,
                         self.wdmm.dogs[0]._gitignore_path)


class AutoRunTrickTestCase(unittest.TestCase):

    def setUp(self):
        self.log_expected = []

    def test_command_property(self):
        handler = AutoRunTrick(command='echo hello')
        self.assertEqual('echo hello', handler.command)

    def test_command_default_cls_attr(self):
        handler = AutoRunTrick()
        expected = ('echo ${event_object} ${event_src_path} is '
                    '${event_type}${if_moved}')
        self.assertEqual(expected, handler._command_default)

    def test_command_default_file_event_substitution(self):
        from watchdog.events import FileCreatedEvent

        handler = AutoRunTrick()
        path = '/source/path'
        event = FileCreatedEvent(path)
        command = handler._substitute_command(event)
        expected = 'echo file /source/path is created'
        self.assertEqual(expected, command)

    def test_command_default_dir_event_substitution(self):
        from watchdog.events import DirMovedEvent

        path = '/source/path'
        dest = '/dest/path'
        handler = AutoRunTrick()
        event = DirMovedEvent(path, dest)
        command = handler._substitute_command(event)
        expected = 'echo directory /source/path/ is moved to /dest/path/'
        self.assertEqual(expected, command)

    def test_command_shell_environment_variables_not_supported(self):
        from watchdog.events import DirMovedEvent

        command = 'echo ${event_dest_path}'
        handler = AutoRunTrick(command)
        path = '/source/path'
        dest = '/dest/path'
        event = DirMovedEvent(path, dest)
        result = handler._substitute_command(event)
        self.assertEqual(command, result)

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
        rstr = ('<AutoRunTrick: command={}, patterns={}, ignore_patterns={}, '
                'ignore_directories={}>').format(*handler.key)
        self.assertEqual(rstr, repr(handler))

    class PipePopen(subprocess.Popen):
        """Mock of subprocess.Popen"""
        def __init__(self, *args, **kwargs):
            super().__init__(*args, stdout=subprocess.PIPE, **kwargs)

    def test_start(self):
        handler = AutoRunTrick('echo hello')
        with patch('subprocess.Popen', new=self.PipePopen):
            handler.start()
        outs, _ = handler._process.communicate()
        self.assertEqual(b'hello\n', outs)

    def test_start_with_event(self):
        from watchdog.events import DirMovedEvent

        handler = AutoRunTrick()
        event = DirMovedEvent('/source/path', '/dest/path')
        with patch('subprocess.Popen', new=self.PipePopen):
            handler.start(event=event)
        outs, _ = handler._process.communicate()
        expected = b'directory /source/path/ is moved to /dest/path/\n'
        self.assertEqual(expected, outs)

    def test_start_with_command_default_and_no_event(self):
        handler = AutoRunTrick('')
        with patch('subprocess.Popen', new=self.PipePopen):
            handler.start()
        outs, _ = handler._process.communicate()
        self.assertEqual('', outs.decode())

    def test_stop(self):
        handler = AutoRunTrick('echo hello')
        handler.start()
        handler.stop()
        self.assertIs(handler._process, None)

    def test_on_any_event(self):
        from watchdog.events import DirMovedEvent

        handler = AutoRunTrick()
        event = DirMovedEvent('/source/path', '/dest/path')
        with patch('subprocess.Popen', new=self.PipePopen):
            handler.on_any_event(event)
        outs, _ = handler._process.communicate()
        expected = b'directory /source/path/ is moved to /dest/path/\n'
        self.assertEqual(outs, expected)

    def _dispatch_test_helper(self, path, ignore_directories=False):
        """patterns: 'relative/path/*.py', 'relative/path/src/'
        ignore_patterns: 'relative/path/*.rst', 'relative/path/__pycache__/',
                         'relative/path/htmlcov/'
        """
        from watchdog import events

        class EchoAutoRunTrick(AutoRunTrick):

            log = []

            def __del__(self):
                del type(self).log

            def on_any_event(self, event):
                type(self).log += ['on_any_event']

            def on_created(self, event):
                type(self).log += ['on_created']

            def on_modified(self, event):
                type(self).log += ['on_modified']

            def on_moved(self, event):
                type(self).log += ['on_moved']

            def on_deleted(self, event):
                type(self).log += ['on_deleted']

        included = ['relative/path/*.py', 'relative/path/src/']
        excluded = ['relative/path/*.rst', 'relative/path/__pycache__/',
                    'relative/path/htmlcov/']
        handler = EchoAutoRunTrick(patterns=included,
                                   ignore_patterns=excluded,
                                   ignore_directories=ignore_directories)
        created = events.FileCreatedEvent(path)
        modified = events.FileModifiedEvent(path)
        deleted = events.FileDeletedEvent(path)
        moved = events.FileMovedEvent(path, 'relative/path/yummy.rst')
        dircreated = events.DirCreatedEvent(path)
        dirmodified = events.DirModifiedEvent(path)
        dirdeleted = events.DirDeletedEvent(path)
        dirmoved = events.DirMovedEvent(path, 'relative/path/htmlcov/')
        fevents = (created, modified, moved, deleted)
        devents = (dircreated, dirmodified, dirmoved, dirdeleted)
        event_types = ['on_created', 'on_modified', 'on_moved', 'on_deleted']

        return handler, fevents, devents, event_types

    def _assert_will_dispatch(self, event, event_type, handler):
        handler.dispatch(event)
        self.log_expected += ['on_any_event', event_type]
        self.assertEqual(handler.log, self.log_expected)

    def _assert_will_not_dispatch(self, event, handler):
        handler.dispatch(event)
        expected = []
        self.assertEqual(handler.log, expected)

    def test_dispatch_file_events_matching_included_patterns(self):
        """All file events should be dispatched."""
        path = 'relative/path/dummy.py'
        handler, fevents, _, event_types = self._dispatch_test_helper(path)

        for event, event_type in zip(fevents, event_types):
            self._assert_will_dispatch(event, event_type, handler)

    def test_dispatch_file_events_matching_ignored_patterns(self):
        """No file event should be dispatched."""
        path = 'relative/path/dummy.rst'
        handler, fevents, _, _ = self._dispatch_test_helper(path)

        for event in fevents:
            self._assert_will_not_dispatch(event, handler)

    def test_dispatch_directory_events_matching_included_patterns(self):
        """All directory events should be dispatched."""
        # Notice no trailing slash is appended.
        # But it's the src path of directory events.
        path = 'relative/path/src'
        handler, _, devents, event_types = self._dispatch_test_helper(path)

        for event, event_type in zip(devents, event_types):
            self._assert_will_dispatch(event, event_type, handler)

    def test_dispatch_directory_events_matching_excluded_patterns(self):
        """No directory events should be dispatched."""
        # Notice no trailing slash is appended.
        # But it's the src path of directory events.
        path = 'relative/path/__pycache__'
        handler, _, devents, _ = self._dispatch_test_helper(path)

        for event in devents:
            self._assert_will_not_dispatch(event, handler)

    def test_dispatch_dir_events_matching_patterns_when_ignore_directories(self):
        """No directory events should be dispatched."""
        # Notice no trailing slash is appended.
        # But it's the src path of directory events.
        path = 'relative/path/src'
        handler, _, devents, _ = self._dispatch_test_helper(
            path, ignore_directories=True
        )

        for event in devents:
            self._assert_will_not_dispatch(event, handler)


class MainTestCase(unittest.TestCase):

    def setUp(self):
        from bark import main
        self.parser = main._create_main_argparser()
        Dog._gitignore_path = './.gitignore'

    def test__create_main_argparser_without_args(self):
        result = self.parser.parse_args([])
        self.assertEqual(
            result,
            Namespace(config=None, gitignore=None, template=False)
        )

    def test__create_main_argparser_with_config_option(self):
        lresult = self.parser.parse_args(['--config-file', 'dogs.py'])
        sresult = self.parser.parse_args(['-c', 'dogs.py'])
        self.assertEqual(lresult, sresult)
        self.assertEqual(
            lresult,
            Namespace(config='dogs.py', gitignore=None, template=False)
        )

    def test__create_main_argparser_with_gitignore_option(self):
        lresult = self.parser.parse_args(['--gitignore', '.gitignore'])
        sresult = self.parser.parse_args(['-g', '.gitignore'])
        self.assertEqual(lresult, sresult)
        self.assertEqual(
            lresult,
            Namespace(config=None, gitignore='.gitignore', template=False)
        )

    def test__create_main_argparser_with_template_option(self):
        lresult = self.parser.parse_args(['--create-wdconfig'])
        sresult = self.parser.parse_args(['-t'])
        self.assertEqual(lresult, sresult)
        self.assertEqual(
            lresult,
            Namespace(config=None, gitignore=None, template=True)
        )

    def test__create_main_argparser_with_unknown_option(self):
        def error(self, *args, **kwargs):
            raise SystemExit

        with patch.object(argparse.ArgumentParser, 'error', new=error) as m:
            self.assertIs(argparse.ArgumentParser.error, m)
            args = ['--unknown-option', 'unknown-option']
            with self.assertRaises(SystemExit):
                self.parser.parse_args(args)

    def test__apply_main_args_with_config_option(self):
        from bark.main import _apply_main_args
        from . import fixture_wdconfig

        expected = fixture_wdconfig.dogs
        arglist = ['--config-file', 'tests/fixture_wdconfig.py']
        args = self.parser.parse_args(arglist)
        wdm = _apply_main_args(args)
        self.assertEqual(expected, wdm.dogs)

        # exit on nonexist config file
        arglist = ['--config-file', 'nonexist_config.py']
        args = self.parser.parse_args(arglist)
        with patch('sys.exit', MagicMock()) as me:
            _apply_main_args(args)
            me.assert_called_once_with("No module named 'nonexist_config'")

    def test__apply_main_args_with_gitignore_option(self):
        from bark.main import _apply_main_args

        arglist = ['-c', 'tests/fixture_wdconfig.py', # suppress sys.exit()
                   '--gitignore', 'tests/fixture_gitignore']
        args = self.parser.parse_args(arglist)
        _apply_main_args(args)
        expected = os.path.join(os.curdir, 'tests/fixture_gitignore')
        self.assertEqual(Dog._gitignore_path, expected)

        # exit on nonexist gitignore file
        arglist = ['-c', 'tests/fixture_wdconfig.py', # suppress sys.exit()
                   '--gitignore', 'nonexist_gitignore']
        args = self.parser.parse_args(arglist)
        with patch('sys.exit', MagicMock()) as me:
            _apply_main_args(args)
            me.assert_called_once_with("File not found: './nonexist_gitignore'")

    def test__apply_main_args_with_template_option(self):
        from bark.main import _apply_main_args
        from tempfile import TemporaryDirectory

        oldwd = os.getcwd()
        with TemporaryDirectory() as td:
            os.chdir(td)
            arglist = ['--create-wdconfig']
            args = self.parser.parse_args(arglist)
            _apply_main_args(args)
            try:
                import wdconfig
            except ImportError:
                os.chdir(oldwd)
                self.fail('wdconfig.py module should exist now.')
            else:
                self.assertEqual(wdconfig.use_gitignore_default, False)
                self.assertEqual(wdconfig.dogs, (Dog(), ))

            # should exit warning wdconfig.py exists
            with patch('sys.exit', MagicMock()) as me:
                _apply_main_args(args)
                me.assert_called_with('wdconfig.py already exists!')
            os.chdir(oldwd)

    def test__apply_main_args_with_no_option(self):
        from tempfile import TemporaryDirectory
        from bark.main import _apply_main_args
        import shutil

        arglist = []
        args = self.parser.parse_args(arglist)
        oldwd = os.getcwd()
        with TemporaryDirectory() as td, \
                patch('sys.exit', MagicMock()) as me:
            os.chdir(td)
            # no wdconfig.py exists
            _apply_main_args(args)
            me.assert_called_once_with("No module named 'wdconfig'")

            # copy a wdconfig.py and parse again
            shutil.copy(os.path.join(oldwd, 'tests/fixture_wdconfig.py'),
                        './wdconfig.py')
            _apply_main_args(args)
            expected = os.path.join(os.curdir, '.gitignore')
            self.assertEqual(Dog._gitignore_path, expected)
            os.chdir(oldwd)


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

    def test_function_keyword_argument_default_value_is_empty_sequence(self):
        """This is a very interesting test.
        It shows the reason to specify the default value of all sequence
        keyword arguments to None, instead of an empty sequence.
        """
        with self.assertRaises(SyntaxError):
            fstr = """
            # This will raise a SyntaxError, saying:
            # name 'g' is parameter and nonlocal
            def f(g=[]):
                nonlocal g
                print(g)
            """
            eval(fstr)
        # From above we see function parameter is nonlocal.
        # When we need a default value for an argument, that is, when we use a
        # keyword argument, and when the argument is a sequence, we have two
        # ways to achieve this.
        # 1. Use empty sequence
        def f(x, l=[]):
            l += [x]
            return l
        self.assertEqual(f(4, [0, 1, 2, 3]), [0, 1, 2, 3, 4])
        self.assertEqual(f(0), [0])
        self.assertEqual(f(1), [0, 1])
        self.assertEqual(f(2), [0, 1, 2])
        # The problem with the above approach is the default value is altered
        # with each call to the function omitting the keyword argument.
        # 2. use None
        def g(x, l=None):
            if l is None:
                l = []
            l += [x]
            return l
        self.assertEqual(g(4, [0, 1, 2, 3]), [0, 1, 2, 3, 4])
        self.assertEqual(g(0), [0])
        self.assertEqual(g(1), [1])
        self.assertEqual(g(2), [2])
        # With the second approach, you get a fresh empty sequence every time
        # you omit the keyword argument, without worrying it will be changed
        # elsewhere.

    def test_local_set_cls_attr_scope(self):
        class C(object):
            cls_attr = None

        c = MagicMock()
        c.C = C
        expected = 'Set in patch.dict'
        with patch.dict('sys.modules', pretty_c=c):
            def f():
                from pretty_c import C as PC

                PC.cls_attr = 'Set in patch.dict'
            f()
            import pretty_c
            self.assertEqual(C.cls_attr, expected)
            self.assertEqual(pretty_c.C.cls_attr, expected)
        self.assertEqual(C.cls_attr, expected)


if __name__ == '__main__':
    unittest.main()
