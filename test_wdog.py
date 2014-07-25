import os
import unittest
from unittest.mock import mock_open, patch

from wdog import Dog


class DogTestCase(unittest.TestCase):

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
        m = mock_open(read_data='*.py[cod]\n# comment line\n__pycache__/\n')
        with patch('builtins.open', m, create=True) as mock:
            result = dog._parse_gitignore()
        patterns = ['*.py[cod]', '__pycache__/']
        mock.assert_called_once_with(os.path.join(os.getcwd(), '.gitignore'))
        self.assertEqual(patterns, result)
