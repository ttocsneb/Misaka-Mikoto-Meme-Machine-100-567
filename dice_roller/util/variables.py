import re

regex = re.compile(r'{([\w.]+)(?:\s*\?\s*(.+))?}')


def _split_variables(text):
    """
    Split a string into each variable component
    """

    separated = list()

    level = 0
    start = 0

    for i, char in enumerate(text):
        if char == '{':
            # Start a new group when level is 0
            if level == 0:
                if start is not i:
                    separated.append(text[start:i])
                start = i
            # Increase a level
            level += 1
        elif char == '}':
            # Start a new group when the depth goes back to 0
            if level == 1:
                separated.append(text[start:i + 1])
                start = i + 1

            # Go down a level with a minimum of 0
            level = max(level - 1, 0)

    # If there is left over text, add it at the end
    if start != len(text):
        separated.append(text[start:])

    return separated


def getVariables(text):
    """
    Get a set of the variables the text uses
    """
    split = _split_variables(text)

    variables = list()

    for t in split:
        result = re.findall(regex, t)
        if result:
            variables.append(result[0][0])
            if result[0][1]:
                variables.extend(getVariables(result[0][1]))
    return set(variables)


def setVariables(text, *args, **kwargs):
    """
    Set variables in a string

    This is similar to the format function, but instead allows for default
    values

    an example of a format variable string would be

    everything after the question mark is the default value if the variable is
    not supplied

    Nested variables are allowed.

    ```
    >>> setVariables('{asdf} {0?foobar} {1?{bam}}', 'a', asdf='b', bam='c')
    'b a c'
    ```
    """
    split = _split_variables(text)

    out = list()

    for t in split:
        result = re.findall(regex, t)
        if result:
            r = result[0]
            try:
                # Try to replace the variable with either the positional arg,
                # or keyword arg
                try:
                    out.append(args[int(r[0])])
                except ValueError:
                    out.append(kwargs[r[0]])
            except (KeyError, IndexError):
                if not r[1]:
                    # There is no default value for a missing variable, raise
                    # the exception
                    raise
                # Replace the variable with the default variable
                out.append(setVariables(r[1], *args, **kwargs))
        else:
            # This is not a variable block, so nothing needs to be done
            out.append(t)

    return ''.join(map(str, out))
