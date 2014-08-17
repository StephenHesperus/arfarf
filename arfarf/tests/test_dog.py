import os
import unittest

from unittest.mock import mock_open, MagicMock, patch

from ..dog import Dog


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
