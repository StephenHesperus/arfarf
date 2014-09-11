"""Define the command to run upon certain file system events.
"""


import os


class Dog(object):
    """Define a command to run upon certain file system events.

    This class contains all the information needed to create a
    PatternMatchingEventHandler, and schedule it to run. You usually define
    instances of this class in your arfarfconfig.py file, but don't manipulate
    its class attributes directly.

    Constructor Args:
        command: A string containing a shell command, it's written exactly the
            same way you write it in a terminal. Example: "echo hello ; echo
            world".
        patterns:
        ignore_patterns:
        ignore_directories: The same as PatternMatchingEventHandler.
        path: The path to monitor, it can be relative or absolute.
        recursive: A boolean indicating if we handle subdirectories events or
            not.
        use_gitignore: A boolean indicating if we use gitignore file to
            provide ignore_patterns or not.

    Attributes:
        use_gitignore_default: A boolean indicating if we use gitignore file
            or not.
        gitignore: A list containing wildcard patterns from gitignore file.
        gitignore_path: A path string pointing to a gitignore file, it can be
            absolute or relative to the current working directory.
        watch_info: Readonly property, a tuple containing information to
            schedule a ObservedWatch.
    """

    use_gitignore_default = False
    gitignore = None
    gitignore_path = os.path.join(os.curdir, '.gitignore')

    def __init__(self, command=None, patterns=None, ignore_patterns=None,
                 ignore_directories=False, path='.', recursive=True,
                 use_gitignore=False):
        self._command = command
        self._patterns = patterns
        self._ignore_patterns = ignore_patterns
        self._ignore_directories = ignore_directories
        self._path = path
        self._recursive = recursive
        self._use_gitignore = use_gitignore

    def __eq__(self, value):
        return isinstance(value, type(self)) and self.key == value.key

    def __ne__(self, value):
        return not self.__eq__(value)

    def __repr__(self):
        return '<Dog: {} {}>'.format(self.key, type(self).gitignore_path)

    @property
    def key(self):
        """Get the tuple to calculate object hash value.

        Returns:
            A tuple containing object attributes.
        """
        patterns = tuple(self._patterns) if self._patterns is not None \
                       else None
        ignore_patterns = tuple(self._ignore_patterns) \
                       if self._ignore_patterns is not None \
                       else None
        return (self._command, patterns, ignore_patterns,
                self._ignore_directories, self._path, self._recursive,
                self._use_gitignore)

    @classmethod
    def parse_gitignore(cls):
        """Parse wildcard patterns from the gitignore file.

        All patterns supported by Git is supported also, except patterns
        starting with a '!', but using '\!' to escape '!' is supported.

        Returns:
            A list containing all the supported patterns.
        """
        gitignore = []
        with open(cls.gitignore_path) as f:
            for line in iter(f.readline, ''):
                drop_chars = (
                    '#', # drop comment lines
                    '\n', # drop blank lines
                    '!' # patterns starting with a '!' is not supported
                        # but "\!" to escape '!' is supported
                )
                if not line.startswith(drop_chars):
                    p = line.strip()
                    # support escape trailing space with a backslash
                    if p.endswith('\\'):
                        p += ' '
                    gitignore.append(p)
        return gitignore

    def create_handler(self, trick_cls):
        """Create a file system event handler providing the handler class.

        Args:
            trick_cls: The handler class to be instantiated, it must be a
                subclass of FileSystemEventHandler.

        Returns:
            The handler object of type of trick_cls.
        """
        use = self._use_gitignore if self._use_gitignore is not None \
              else type(self).use_gitignore_default
        if use:
            if type(self).gitignore is None:
                type(self).gitignore = type(self).parse_gitignore()
        gip = type(self).gitignore if type(self).gitignore is not None \
              else []
        selfip = [] if self._ignore_patterns is None \
                 else self._ignore_patterns
        ipatterns = gip + selfip
        included = [os.path.join(self._path, p) for p in self._patterns] \
                   if self._patterns is not None else None
        excluded = [os.path.join(self._path, p) for p in ipatterns] \
                   if ipatterns else None
        return trick_cls(command=self._command,
                         patterns=included, ignore_patterns=excluded,
                         ignore_directories=self._ignore_directories)

    @property
    def watch_info(self):
        """Readonly, information needed to create the ObservedWatch.
        """
        return (self._path, self._recursive)
