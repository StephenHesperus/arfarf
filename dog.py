import os


class Dog(object):

    _use_gitignore_default = False
    _gitignore = None
    _gitignore_path = os.path.join(os.curdir, '.gitignore')

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
        return '<Dog: {} {}>'.format(self.key, type(self)._gitignore_path)

    @property
    def key(self):
        patterns = tuple(self._patterns) if self._patterns is not None \
                       else None
        ignore_patterns = tuple(self._ignore_patterns) \
                       if self._ignore_patterns is not None \
                       else None
        return (self._command, patterns, ignore_patterns,
                self._ignore_directories, self._path, self._recursive,
                self._use_gitignore)

    @classmethod
    def set_gitignore_path(cls, path):
        cls._gitignore_path = path

    @classmethod
    def reset_gitignore_path(cls):
        cls._gitignore_path = os.path.join(os.curdir, '.gitignore')

    @classmethod
    def _parse_gitignore(cls):
        gitignore = []
        with open(cls._gitignore_path) as f:
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
        use = self._use_gitignore if self._use_gitignore is not None \
              else type(self)._use_gitignore_default
        if self._use_gitignore:
            if type(self)._gitignore is None:
                type(self)._gitignore = type(self)._parse_gitignore()
        gip = type(self)._gitignore if type(self)._gitignore is not None \
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
        return (self._path, self._recursive)
