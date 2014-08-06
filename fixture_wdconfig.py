from wdog import Dog as dog

dogs = (
    dog(command='echo hello world', use_gitignore=True),
    dog(command='echo nice to meet you', patterns=['*.py'],
        ignore_directories=True),
)
