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
