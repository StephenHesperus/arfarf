class ArfTestCase(unittest.TestCase):

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