import os


class Dog(object):
    def __init__(self, command='', patterns=['*'], ignore_patterns=[],
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

    def _sort(self):
        dog_dict = {}
        for dog in self._dogs:
            wi = dog.watch_info
            if wi in dog_dict:
                dog_dict[wi].append(dog)
            else:
                dog_dict[wi] = [dog]

        return dog_dict
