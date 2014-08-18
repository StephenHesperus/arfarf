import os

from collections import defaultdict

from .dog import Dog


class WDConfigParser(object):
    """
    Parser for arfarfconfig.py file.
    """

    def __init__(self, config_module):
        self._dogs = config_module.dogs
        self._use_gitignore_default = config_module.use_gitignore_default
        self._gitignore_path = config_module.gitignore_path
        self._config_module = config_module

    def _set_use_gitignore_default(self):
        Dog.use_gitignore_default = self._use_gitignore_default

    def _set_gitignore_path(self):
        Dog.gitignore_path = os.path.join(os.curdir, self._gitignore_path)

    def schedule_with(self, observer, cls):
        self._set_use_gitignore_default()
        self._set_gitignore_path()

        handler_for_watch = defaultdict(set)
        for dog in self._dogs:
            handler = dog.create_handler(cls)
            watch = observer.schedule(handler, *dog.watch_info)
            handler_for_watch[watch].add(handler)
        handler_for_watch = dict(handler_for_watch)

        return handler_for_watch
