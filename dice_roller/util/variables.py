from dice_roller.parser.lexer import NameRule


def getVariables(text: str):
    """
    Get a set of the variables the text uses
    """
    variables = set()

    for t in text.split('$')[1:]:
        token = NameRule.parse(t)
        if token:
            variables.add(token.content)
    return set(variables)


