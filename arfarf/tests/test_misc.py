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
