import os
import signal
import subprocess
import time

from watchdog.tricks import Trick


class Dog(object):
    def __init__(self, command, patterns=['*'], ignore_patterns=[],
                 ignore_directories=False, path='.', recursive=True,
                 use_gitignore=False):
        self._command = command
        self._patterns = patterns
        self._ignore_patterns = ignore_patterns
        self._ignore_directories = ignore_directories
        self._path = path
        self._recursive = recursive
        self._use_gitignore = use_gitignore

    def _parse_gitignore(self):
        with open(os.path.join(os.getcwd(), '.gitignore')) as f:
            lines = f.readlines()
        gitignore = []
        for line in lines:
            if not line.startswith('#'):
                gitignore.append(line.strip())
        return gitignore

    def create_handler(self, cls):
        if self._use_gitignore:
            gitignore = self._parse_gitignore()
            self._ignore_patterns.extend(gitignore)
        return cls(command=self._command, patterns=self._patterns,
                   ignore_patterns=self._ignore_patterns,
                   ignore_directories=self._ignore_directories)

    @property
    def watch_info(self):
        return (self._path, self._recursive)


class WDConfigParser(object):
    """
    Parser for wdconfig.py file.
    """

    def __init__(self, dogs):
        self._dogs = dogs

    def schedule_with(self, observer, cls):
        handler_for_watch = {}
        for dog in self._dogs:
            handler = dog.create_handler(cls)
            watch = observer.schedule(handler, *dog.watch_info)
            if watch in handler_for_watch:
                handler_for_watch[watch].add(handler)
            else:
                handler_for_watch[watch] = set([handler])

        return handler_for_watch


class AutoRunTrick(Trick):
    """
    A variant of AutoRestartTrick.
    """

    def __init__(self, command, patterns=['*'], ignore_patterns=[],
                 ignore_directories=False, stop_signal=signal.SIGINT,
                 kill_after=10):
        super().__init__(patterns, ignore_patterns, ignore_directories)
        self._command = command
        self._stop_signal = stop_signal
        self._kill_after = kill_after
        self._process = None

    @property
    def command(self):
        return self._command

    def start(self):
        self._process = subprocess.Popen(self._command, shell=True,
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
        self.start()

    @property
    def key(self):
        return (self.command,
                tuple(self.patterns), tuple(self.ignore_patterns),
                self.ignore_directories)

    def __eq__(self, value):
        return isinstance(value, self.__class__) and self.key == value.key

    def __ne__(self, value):
        return not self.__eq__(value)

    def __hash__(self):
        return hash(self.key)

    def __repr__(self):
        repr_str = ('<AutoRunTrick: command={}, patterns={}, ignore_patterns={},'
                'ignore_directories={}>').format(*self.key)
        return repr_str


def main(observer, dogs):
    """Script entry point."""

    parser = WDConfigParser(dogs)
    handler_for_watch = parser.schedule_with(observer, AutoRunTrick)
    handlers = set.union(*tuple(handler_for_watch.values()))

    for handler in handlers:
        handler.start()
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
    for handler in handlers:
        handler.stop()


if __name__ == '__main__':
    from watchdog.observers.polling import PollingObserver
    from wdconfig import dogs

    # The reason to use PollingObserver() is it's os-independent
    # and the default Observer() generates two identical modified event when
    # modifying a file.
    observer = PollingObserver()
    main(observer, dogs)
