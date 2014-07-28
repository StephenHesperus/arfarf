"""
Configuration file for wdog.
``dogs`` is a tuple of wdog.Dog objects.
"""

from wdog import Dog as dog


dogs = (
    # examples
    ## this dog shows the default values for each argument
    dog(command='', patterns=['*'], ignore_patterns=[],
        ignore_directories=False, path='.', recursive=True,
        use_gitignore=False),
    ## this dog shows the same default values without using keywords
    # dog('echo hello', ['*.py'], [], False, '.', True, True),
    # dog(command='echo Hello, World!', ignore_directories=True,
    #     use_gitignore=True),
    # dog('echo hello', ['*.py'], use_gitignore=True),
    # dog(command='echo hello', patterns=['*.py'], use_gitignore=True),
)
