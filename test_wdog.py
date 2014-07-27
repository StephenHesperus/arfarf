import os
import unittest
from unittest.mock import mock_open, patch, sentinel

import watchdog.events
from watchdog.observers import Observer
from watchdog.observers.api import ObservedWatch

import wdconfig
from wdog import Dog, WDConfigParser, AutoRunTrick


class DogTestCase(unittest.TestCase):

    def setUp(self):
        m = mock_open(read_data='*.py[cod]\n# comment line\n__pycache__/\n')
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
        except:
            self.fail(__doc__)

    def test__parse_gitignore(self):
        dog = Dog()
        result = dog._parse_gitignore()
        patterns = ['*.py[cod]', '__pycache__/']
        self.gitignore_mock.assert_called_once_with(
            os.path.join(os.getcwd(), '.gitignore')
        )
        self.assertEqual(patterns, result)

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
                ignore_patterns=['more_ipattern',
                                 '*.py[cod]', '__pycache__/'],
                ignore_directories=True
            )

    def test_watch_info_property(self):
        dog = Dog()
        winfo = dog.watch_info
        self.assertEqual(winfo, ('.', True))

        dog = Dog(path='/dummy/path', recursive=False)
        winfo = dog.watch_info
        self.assertEqual(winfo, ('/dummy/path', False))


class WDConfigParserTestCase(unittest.TestCase):
    """Test wdog module functions."""

    def setUp(self):
        from wdog import Dog as dog
        dogs_mock = (
            dog(command='echo dog1', path='.', recursive=True),
            dog(command='echo dog2', path='.', recursive=True),
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


class AutoRunTrickTestCase(unittest.TestCase):
    """
    The only difference between AutoRunTrick and AutoRestartTrick is the way
    they handle command parsing and execution. So the this test case only
    focus on it.
    """

    def test_command_property(self):
        handler = AutoRunTrick(command='echo hello')
        self.assertEqual('echo hello', handler.command)

    def test_equality(self):
        handler1 = AutoRunTrick(command='echo hello')
        handler2 = AutoRunTrick(command='echo hello')

        self.assertEqual(handler1, handler2)

    def test_hashable(self):
        import collections
        handler = AutoRunTrick(command='echo hello')
        self.assertTrue(isinstance(handler, collections.Hashable))
