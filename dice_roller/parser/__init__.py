from . import functions as functs

from typing import List, Dict


def parseString(text: str, context=None) -> int:
    from . import lexer, parser
    if not context:
        context = Context()
    lex = lexer.Lexer(text)
    lex.parseAll()
    lex.filterOut(lexer.WHITESPACE)

    par = parser.Parser(lex.getOutput(), text)
    par.parseAll()
    return par.operate(context)


class Context:
    default_functions = [
        functs.IfFunction(),
        functs.AndFunction(),
        functs.OrFunction(),
        functs.EqFunction(),
        functs.NotFunction(),
        functs.MaxFunction(),
        functs.MinFunction(),
        functs.AdvFunction(),
        functs.TopFunction(),
        functs.BotFunction()
    ]

    def __init__(self,
                 args: List[int] = None,
                 functions: List[functs.Function] = None,
                 variables: Dict[str, int] = None):
        self.args = args or list()
        self.functions = dict()
        functs = self.default_functions

        if isinstance(functions, list):
            functs += functions
        elif isinstance(functions, dict):
            self.functions.update(functions)
        self.functions.update(dict((func.name, func) for func in functs))

        self.variables = variables or dict()
