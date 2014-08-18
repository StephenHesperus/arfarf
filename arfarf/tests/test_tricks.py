import unittest
import subprocess

from unittest.mock import patch

from ..tricks import AutoRunTrick


class AutoRunTrickTestCase(unittest.TestCase):

    def setUp(self):
        self.log_expected = []

        from io import StringIO
        self.patcher = patch('sys.stdout', new_callable=StringIO)
        self.mock_out = self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_command_property(self):
        handler = AutoRunTrick(command='echo hello')
        self.assertEqual('echo hello', handler.command)

    def test_command_default_cls_attr(self):
        expected = ('${event_object} ${event_src_path} is '
                    '${event_type}${if_moved}')
        self.assertEqual(expected, AutoRunTrick.command_default)

    def test_command_default_file_event_substitution(self):
        from watchdog.events import FileCreatedEvent

        handler = AutoRunTrick()
        path = '/source/path'
        event = FileCreatedEvent(path)
        command = handler._substitute_command(event)
        expected = 'file /source/path is created'
        self.assertEqual(expected, command)

    def test_command_default_dir_event_substitution(self):
        from watchdog.events import DirMovedEvent

        path = '/source/path'
        dest = '/dest/path'
        handler = AutoRunTrick()
        event = DirMovedEvent(path, dest)
        command = handler._substitute_command(event)
        expected = 'directory /source/path/ is moved to /dest/path/'
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

    def test_start_with_command_not_default_and_event(self):
        """Command not default should execute."""
        from watchdog.events import FileCreatedEvent

        path = '/source/path'
        event = FileCreatedEvent(path)
        handler = AutoRunTrick('echo hello')
        with patch('subprocess.Popen', new=self.PipePopen):
            handler.start(event=event)
        outs, _ = handler._process.communicate()
        self.assertEqual(b'hello\n', outs)

    def test_start_with_command_not_default_and_no_event(self):
        """Command not default should execute."""
        handler = AutoRunTrick('echo hello')
        with patch('subprocess.Popen', new=self.PipePopen):
            handler.start()
        outs, _ = handler._process.communicate()
        self.assertEqual(b'hello\n', outs)

    def test_start_with_command_default_and_event(self):
        """Default command only execute when there's an event."""
        from watchdog.events import DirMovedEvent

        handler = AutoRunTrick()
        event = DirMovedEvent('/source/path', '/dest/path')
        handler.start(event=event)
        expected = 'directory /source/path/ is moved to /dest/path/\n'
        self.assertEqual(expected, self.mock_out.getvalue())

    def test_start_with_command_default_and_no_event(self):
        """Default command should not execute when there's no event."""
        handler = AutoRunTrick()
        handler.start()
        self.assertEqual('', self.mock_out.getvalue())

    def test_command_default_executed_on_each_event(self):
        """Default logging command should execute once on each event."""
        from watchdog.events import FileCreatedEvent, DirModifiedEvent

        handler = AutoRunTrick()
        file_e = FileCreatedEvent('/source/path/file')
        dir_e = DirModifiedEvent('/source/path')
        handler.dispatch(file_e)
        handler.dispatch(dir_e)
        expected = ('file /source/path/file is created\n'
                    'directory /source/path/ is modified\n')
        self.assertEqual(expected, self.mock_out.getvalue())

    def test_stop(self):
        handler = AutoRunTrick('echo hello')
        handler.start()
        handler.stop()
        self.assertIs(handler._process, None)

    def test_on_any_event(self):
        from watchdog.events import DirMovedEvent

        handler = AutoRunTrick(command='echo hello')
        event = DirMovedEvent('/source/path', '/dest/path')
        with patch('subprocess.Popen', new=self.PipePopen):
            handler.on_any_event(event)
        outs, _ = handler._process.communicate()
        expected = b'hello\n'
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
