from collections import defaultdict


class WDConfigParser(object):
    """
    Parser for wdconfig.py file.
    """

    def __init__(self, wdconfig_module):
        self._dogs = wdconfig_module.dogs
        self._use_gitignore_default = wdconfig_module.use_gitignore_default
        self._wdconfig = wdconfig_module

    def _set_use_gitignore_default(self):
        from dog import Dog
        Dog._use_gitignore_default = self._use_gitignore_default

    def schedule_with(self, observer, cls):
        self._set_use_gitignore_default()

        handler_for_watch = defaultdict(set)
        for dog in self._dogs:
            handler = dog.create_handler(cls)
            watch = observer.schedule(handler, *dog.watch_info)
            handler_for_watch[watch].add(handler)
        handler_for_watch = dict(handler_for_watch)

        return handler_for_watch