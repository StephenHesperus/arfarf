import os
import signal
import subprocess
import time

from string import Template
from watchdog.utils import unicode_paths

from pathtools.patterns import match_any_paths
from watchdog.tricks import Trick
from watchdog.events import EVENT_TYPE_CREATED, EVENT_TYPE_MODIFIED
from watchdog.events import EVENT_TYPE_MOVED, EVENT_TYPE_DELETED



class AutoRunTrick(Trick):
    """
    A variant of AutoRestartTrick.
    When called without arguments, it's the same as a logger of file system
    events.
    """

    command_default = ('${event_object} ${event_src_path} is '
                        '${event_type}${if_moved}')

    def __init__(self, command=None, patterns=None, ignore_patterns=None,
                 ignore_directories=False, stop_signal=signal.SIGINT,
                 kill_after=10):
        # Match Trick.__init__() signature.
        super().__init__(patterns, ignore_patterns, ignore_directories)
        self._command = command
        self._stop_signal = stop_signal
        self._kill_after = kill_after
        self._process = None

    def __eq__(self, value):
        return isinstance(value, self.__class__) and self.key == value.key

    def __ne__(self, value):
        return not self.__eq__(value)

    def __hash__(self):
        return hash(self.key)

    def __repr__(self):
        rstr = ('<AutoRunTrick: command={}, patterns={}, ignore_patterns={}, '
                'ignore_directories={}>').format(*self.key)
        return rstr

    @staticmethod
    def _add_dir_t_slash(event, path):
        """Add trailing slash if event is directory event."""
        if event.is_directory:
            path = os.path.join(path, '')
        return path


    def _substitute_command(self, event):
        # Only default logging command supports substitution
        if self._command is not None:
            return self._command
        if event is None:
            return '' # do nothing

        # dest = event.dest_path if hasattr(event, 'dest_path') else ''
        if hasattr(event, 'dest_path'):
            dest_path = self._add_dir_t_slash(event, event.dest_path)
        else:
            dest_path = ''
        if event.src_path:
            src_path = self._add_dir_t_slash(event, event.src_path)
        event_obj = 'directory' if event.is_directory else 'file'
        if_moved = ' to %s' % dest_path if dest_path else ''
        context = {
            'event_object': event_obj,
            'event_src_path': src_path,
            'event_type': event.event_type,
            'event_dest_path': dest_path,
            'if_moved': if_moved,
        }
        c = Template(type(self).command_default).safe_substitute(**context)
        return c

    @property
    def command(self):
        return self._command

    def start(self, event=None):
        command = self._substitute_command(event)
        if self._command is None and command:
            print(command) # logging only on events
        else:
            self._process = subprocess.Popen(command, shell=True,
                                             start_new_session=True)

    def stop(self):
        if self._process is None:
            return
        try:
            os.killpg(os.getpgid(self._process.pid), self._stop_signal)
        except OSError:
            # Process is already gone.
            pass
        else:
            kill_time = time.time() + self._kill_after
            while time.time() < kill_time:
                if self._process.poll() is not None:
                    break
                time.sleep(0.25)
            else:
                try:
                    os.killpg(os.getpgid(self._process.pid, signal.SIGKILL))
                except OSError:
                    pass
        self._process = None

    def on_any_event(self, event):
        self.stop()
        self.start(event=event)

    @property
    def key(self):
        if self.patterns is None:
            patterns = None
        else:
            patterns = tuple(self.patterns)
        if self.ignore_patterns is None:
            ignore_patterns = None
        else:
            ignore_patterns = tuple(self.ignore_patterns)
        return (self.command,
                patterns, ignore_patterns,
                self.ignore_directories)

    def dispatch(self, event):
        if event.is_directory and self._ignore_directories:
            return

        paths = []
        if hasattr(event, 'dest_path'):
            dest_path = self._add_dir_t_slash(event, event.dest_path)
            paths.append(unicode_paths.decode(dest_path))
        if event.src_path:
            src_path = self._add_dir_t_slash(event, event.src_path)
            paths.append(unicode_paths.decode(src_path))

        if match_any_paths(paths,
                           included_patterns=self._patterns,
                           excluded_patterns=self._ignore_patterns,
                           case_sensitive=self.case_sensitive):
            self.on_any_event(event)
            method_map = {
                EVENT_TYPE_CREATED: self.on_created,
                EVENT_TYPE_MODIFIED: self.on_modified,
                EVENT_TYPE_MOVED: self.on_moved,
                EVENT_TYPE_DELETED: self.on_deleted,
            }
            event_type = event.event_type
            method_map[event_type](event)
