from typing import List


def process(context, arg) -> int:
    from . import parser
    if isinstance(arg, parser.OperableRule):
        return arg.operate(context)
    elif isinstance(arg, str):
        from . import parseString
        return parseString(arg)
    return arg


def processArgs(context, args) -> List[int]:
    return [process(context, arg) for arg in args]


class Function:
    def __init__(self, name: str, func: str):
        from . import lexer, parser
        self.name = name
        self.raw = func
        lex = lexer.Lexer(self.raw)
        lex.parseAll()
        lex.filterOut(lexer.WHITESPACE)

        self.parser = parser.Parser(lex.getOutput(), self.raw)
        self.parser.parseAll()

    def call(self, context, args) -> int:
        from . import Context
        args = processArgs(context, args)
        ctx = Context(args, context.functions, context.variables)
        return self.parser.operate(ctx)


class IfFunction(Function):
    """
    Choose between two results:

    ```excel
    if(condition, ifTrue, ifFalse)
    if(1, 5, 1) => 5
    if(0, 5, 1) => 1
    ```
    """
    def __init__(self):
        self.name = "if"

    def call(self, context, args) -> int:
        first = process(context, args[0])
        ifTrue = args[1]
        ifFalse = args[2]

        if first != 0:
            return process(context, ifTrue)
        return process(context, ifFalse)


class AndFunction(Function):
    """
    Check if all values are true

    ```
    and(...)
    and(5 > 1, 5 < 10) => 1
    and(5 > 1, 5 < 10, 5 = 5) => 1
    and(20 > 1, 20 < 10) => 0
    ```
    """
    def __init__(self):
        self.name = "and"

    def call(self, context, args) -> int:
        args = all(process(context, arg) != 0 for arg in args)
        return 1 if args else 0


class OrFunction(Function):
    """
    Check if all values are true

    ```
    or(...)
    or(5 < 1, 5 > 10) => 0
    or(5 < 1, 5 > 10, 5 = 5) => 1
    or(20 < 1, 20 > 10) => 1
    ```
    """
    def __init__(self):
        self.name = "or"

    def call(self, context, args) -> int:
        args = any(process(context, arg) != 0 for arg in args)
        return 1 if args else 0


class NotFunction(Function):
    """
    Invert a boolean value

    ```
    not(a)
    not(1) => 0
    not(0) => 1
    ```
    """
    def __init__(self):
        self.name = "not"

    def call(self, context, args) -> int:
        arg = process(context, args[0]) == 0
        return 1 if arg else 0


class EqFunction(Function):
    """
    Check if all values are equal to each other

    ```
    eq(...)
    eq(5, 5) => 1
    eq(5, 6) => 0
    eq(5, 5, 5, 5, 5) => 1
    eq(5, 5, 5, 5, 4) => 0
    ```
    """
    def __init__(self):
        self.name = "eq"

    def call(self, context, args) -> int:
        args = processArgs(context, args)
        equal = args[0]
        for arg in args:
            if equal is not arg:
                return 0
        return 1
