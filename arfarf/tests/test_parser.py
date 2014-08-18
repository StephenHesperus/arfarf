import unittest

from unittest.mock import MagicMock, patch, sentinel, mock_open

from watchdog.observers import Observer
from watchdog.observers.api import ObservedWatch

from ..dog import Dog
from ..parser import WDConfigParser


class WDConfigParserTestCase(unittest.TestCase):

    def setUp(self):
        from ..dog import Dog as dog
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
        self.patcher = patch.dict('sys.modules', config_module=self.wdmm)
        self.patcher.start()
        import config_module
        self.parser = WDConfigParser(config_module)
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
        self.parser.gitignore_path = '.gitignore'
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

    def test_construct_using_config_module(self):
        import config_module

        self.assertIsNotNone(self.parser._config_module)
        self.assertIs(self.parser._config_module, config_module)

    def test_can_set_Dog_use_gitignore_defaut_cls_attr(self):
        use = self.parser._use_gitignore_default # True
        self.parser._set_use_gitignore_default()
        self.assertEqual(use, Dog._use_gitignore_default)
        # newly created Dog() _use_gitignore_default is changed
        dog = Dog()
        self.assertEqual(dog._use_gitignore_default, use)
        # _use_gitignore_default of dogs in config_module are changed
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
        # self.parser.gitignore_path is '.gitignore'
        self.assertEqual(Dog.gitignore_path, './.gitignore')

        # change gitignore file path to .bzrignore
        self.wdmm.gitignore_path = '.bzrignore'
        parser = WDConfigParser(self.wdmm)
        parser._set_gitignore_path()
        self.assertEqual('./.bzrignore', Dog.gitignore_path)
        dog = Dog()
        self.assertEqual(dog.gitignore_path,
                         self.wdmm.dogs[0].gitignore_path)
