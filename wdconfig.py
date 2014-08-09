"""
Configuration file for wdog.
``dogs`` is a tuple of wdog.Dog objects.

Usage
=====
Add "dog(...)," lines to the dogs variable, the keyword arguments should be
self-explanatory. Note the comma "," at the end, it is mandatory. You can omit
the keywords if you treat all the arguments positional. You can omit the
default value arguments if you only use keyword arguments.

Arguments:
command             a string of shell command exactly the same as what you
                    type in terminal
patterns            a list of shell pattern strings to monitor
ignore_patterns     a list of shell patterns to ignore
ignore_directories  True/False, ignore directory modifications or not
path                the path string this dog monitors
recursive           True/False, traverse into subdirectories or not
use_gitignore       True/False, if Git is used, its ignore patterns can be
                    used as an complement to ignore_patterns; it needs the
                    .gitignore file sits under the same directory where the
                    wdog.py script is run, usually that's the root of your
                    project
"""

# from wdog import Dog as dog
from dog import Dog as dog


dogs = (
    # examples
    ## this dog shows the default values for each argument
    # dog(command='', patterns=['*'], ignore_patterns=[],
        # ignore_directories=False, path='.', recursive=True,
        # use_gitignore=False),

    ## this dog shows the same default values without using keywords
    # dog('echo hello', ['*.py'], [], False, '.', True, True),

    ## those are other different way to specific a dog
    # dog(command='echo Hello, World!', ignore_directories=True,
    #     use_gitignore=True),
    # dog('echo hello', ['*.py'], use_gitignore=True),
    # dog(command='echo hello', patterns=['*.py'], use_gitignore=True),
)
