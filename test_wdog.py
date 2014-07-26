import os
import unittest
from unittest.mock import mock_open, patch

from wdog import Dog


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
