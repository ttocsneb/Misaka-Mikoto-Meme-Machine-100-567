from typing import List

from dice_roller.util import dice

from . import lexer
from . import Context

tokenList = List[lexer.Token]

###############################################################################
#
# Recursive Descent Parser Algorithm
#
# StartRule ::= ValRule ComRule
# ComRule ::= (= | <> | < | > | <= | >=) ValRule ComRule | AddRule
# AddRule ::= [+-] ValRule AddRule | MulRule
# MulRule ::= [*/%] ValRule MulRule | ExpRule
# ExpRule ::= ^ ValRule ExpRule | RanRule
# RanRule ::= d ValRule RanRule | lambda
#
# ValRule ::= UnaryRule | ValueRule
# UnaryRule ::= - ValueRule
# ValueRule ::= VarRule | FuncRule | ParRule | NUM
#
# VarRule ::= $ (NAME | NUM) option
# option ::= ? ValRule | lambda
#
# FuncRule ::= NAME ( args )
# args ::= ValRule arglist | lambda
# arglist ::= , ValRule arglist | lambda
#
# ParRule ::= ( StartRule )
#
###############################################################################
#
# Note that because this takes into account the order of operations,
# This RDP will need to be run in a special way to properly parse an equation:
#   1: StartRule
#   2: ComRule
#   3: ComRule
#   i: ComRule
#
# When calculating the result, feed the result of each group into the next:
#   1: result = StartRule()
#   2: result = ComRule(result)
#   3: result = ComRule(result)
#   i: result = ComRule(result)
#
###############################################################################


def toBool(val) -> int:
    return 1 if val else 0


def getToken(tokens, index):
    if index >= len(tokens):
        return tokens[-1]
    return tokens[index]


def compareToken(tokens, index, expected):
    if index >= len(tokens):
        return False
    if isinstance(expected, list):
        return tokens[index].tokenType in expected
    return tokens[index].tokenType == expected


class Rule:
    def peek(self, tokens: tokenList, index: int) -> bool:
        raise NotImplementedError

    def parse(self, tokens: tokenList, index: int, text: str) -> int:
        raise NotImplementedError


class OperableRule(Rule):
    def operate(self, context: Context):
        raise NotImplementedError


class CalculateRule(Rule):
    def calculate(self, context: Context, first: int):
        raise NotImplementedError


class OperatorRule(Rule):
    operatorFunctions = {
        lexer.ADD: lambda a, b: a + b,
        lexer.SUB: lambda a, b: a - b,
        lexer.DIV: lambda a, b: a // b,
        lexer.MUL: lambda a, b: a * b,
        lexer.MOD: lambda a, b: a % b,
        lexer.EXP: lambda a, b: a ** b,
        lexer.DICE: lambda a, b: dice.roll_sum(b, a)[0],
        lexer.EQ: lambda a, b: toBool(a == b),
        lexer.NE: lambda a, b: toBool(a != b),
        lexer.LE: lambda a, b: toBool(a <= b),
        lexer.GE: lambda a, b: toBool(a >= b),
        lexer.L: lambda a, b: toBool(a < b),
        lexer.G: lambda a, b: toBool(a > b)
    }

    def __init__(self, operators: List[int]):
        self.operators = operators
        self.function = None

    def peek(self, tokens: tokenList, index: int) -> bool:
        if index >= len(tokens):
            return False
        return tokens[index].tokenType in self.operators

    def parse(self, tokens: tokenList, index: int, text: str):
        if tokens[index].tokenType in self.operators:
            self.function = self.operatorFunctions[tokens[index].tokenType]
            return 1
        else:
            raise lexer.InvalidToken("Expected Operator", tokens[index], text)


class OperationRule(CalculateRule):
    def __init__(self, operators: List[int],
                 otherOperation=None):
        self.operator = OperatorRule(operators)
        self.other = otherOperation
        self.next = None
        self.value = ValRule()

    def peek(self, tokens: tokenList, index: int) -> bool:
        if self.other:
            return self.operator.peek(tokens, index) \
                    or self.other.peek(tokens, index)
        return True

    def parse(self, tokens: tokenList, index: int, text: str) -> int:
        self.operator.function = None
        size = 0
        if not self.operator.peek(tokens, index + size):
            if self.other:
                return self.other.parse(tokens, index + size, text)
            return 0
        size = self.operator.parse(tokens, index + size, text)

        size += self.value.parse(tokens, index + size, text)

        self.next = self.__class__()
        nextSize = self.next.parse(tokens, index + size, text)
        if nextSize == 0:
            self.next = None
        size += nextSize

        return size

    def calculate(self, context: Context, first: int) -> int:
        """
        Calculate the result of this operation.
        If there is a next operation, calculate that one as well

        Keep in mind that the calculate operation should be able to run
        in reverse order of what was parsed
        """

        if self.operator.function:
            if self.next:
                second = self.next.calculate(
                    context, self.value.operate(context)
                )
                return self.operator.function(first, second)
            return self.operator.function(first, self.value.operate(context))

        # If self.other is None, there is a problem with the parsing
        return self.other.calculate(context, first)


class ComRule(OperationRule):
    def __init__(self):
        super().__init__([
            lexer.EQ, lexer.NE, lexer.LE, lexer.GE, lexer.L, lexer.G
        ], AddRule())


class AddRule(OperationRule):
    def __init__(self):
        super().__init__([lexer.ADD, lexer.SUB], MulRule())


class MulRule(OperationRule):
    def __init__(self):
        super().__init__([lexer.MUL, lexer.DIV, lexer.MOD], ExpRule())


class ExpRule(OperationRule):
    def __init__(self):
        super().__init__([lexer.EXP], DiceRule())


class DiceRule(OperationRule):
    def __init__(self):
        super().__init__([lexer.DICE])


class NumRule(OperableRule):
    def __init__(self):
        self.value = None

    @classmethod
    def peek(cls, tokens: tokenList, index: int) -> bool:
        if index >= len(tokens):
            return False
        return tokens[index].tokenType == lexer.NUMBER

    def parse(self, tokens: tokenList, index: int, text: str) -> int:
        lexer.assertTerminal(
            "Expected number", lexer.NUMBER, tokens[index], text
        )
        self.value = tokens[index].content
        return 1

    def operate(self, context: Context) -> int:
        return int(self.value)


class ParRule(OperableRule):
    def __init__(self):
        self.start = Parser()

    @classmethod
    def peek(cls, tokens: tokenList, index: int) -> bool:
        if index >= len(tokens):
            return False
        return tokens[index].tokenType == lexer.L_PAREN

    def parse(self, tokens: tokenList, index: int, text: str) -> int:
        lexer.assertTerminal(
            "Expected '('", lexer.L_PAREN, tokens[index], text
        )
        size = 1

        size += self.start.parse(tokens, index + size, text)

        lexer.assertTerminal(
            "Expected ')'", lexer.R_PAREN, getToken(tokens, index + size), text
        )
        size += 1
        return size

    def operate(self, context: Context) -> int:
        return self.start.operate(context)


class VarRule(OperableRule):
    def __init__(self):
        self.variable = None
        self.default = ValRule()
        self.default_given = False

    @classmethod
    def peek(cls, tokens: tokenList, index: int) -> bool:
        if index >= len(tokens):
            return False
        return tokens[index].tokenType == lexer.DOLLAR

    def parse(self, tokens: tokenList, index: int, text: str) -> int:
        self.default_given = False
        lexer.assertTerminal("Expected '$'", lexer.DOLLAR, tokens[index], text)
        lexer.assertTerminal(
            "Expected name", [lexer.NAME, lexer.NUMBER], tokens[index + 1],
            text
        )
        self.variable = tokens[index + 1]

        size = 2

        if index + size < len(tokens) \
                and compareToken(tokens, index + size, lexer.Q_MARK):
            size += 1
            size += self.default.parse(tokens, index + size, text)
            self.default_given = True

        return size

    def operate(self, context: Context) -> int:

        def getVar():
            if self.variable.tokenType == lexer.NUMBER:
                return context.args[int(self.variable.content) - 1]
            return context.variables[self.variable.content]

        if self.default_given:
            try:
                return getVar()
            except KeyError:
                return self.default.operate(context)
            except IndexError:
                return self.default.operate(context)
        return getVar()


class FuncRule(OperableRule):
    def __init__(self):
        self.name = ""
        self.params = list()

    @classmethod
    def peek(cls, tokens: tokenList, index: int) -> bool:
        if index >= len(tokens):
            return False
        return tokens[index].tokenType == lexer.NAME

    def parse(self, tokens: tokenList, index: int, text: str) -> int:
        lexer.assertTerminal("expected name", lexer.NAME, tokens[index], text)
        self.name = tokens[index].content
        lexer.assertTerminal(
            "expected '('", lexer.L_PAREN, getToken(tokens, index + 1), text
        )

        size = 2

        if not compareToken(tokens, index + size, lexer.R_PAREN):
            loop = True
            while loop:
                self.params.append(Parser())
                size += self.params[-1].parse(tokens, index + size, text)
                if compareToken(tokens, index + size, lexer.COMMA):
                    size += 1
                else:
                    loop = False

        lexer.assertTerminal(
            "expected ')'", lexer.R_PAREN, getToken(tokens, index + size), text
        )
        size += 1

        return size

    def operate(self, context: Context) -> int:
        return context.functions[self.name].call(context, self.params)


class ValueRule(OperableRule):
    values = {
        lexer.NUMBER: NumRule,
        lexer.L_PAREN: ParRule,
        lexer.DOLLAR: VarRule,
        lexer.NAME: FuncRule
    }

    def __init__(self):
        self.value = None

    @classmethod
    def peek(cls, tokens: tokenList, index: int) -> bool:
        if index >= len(tokens):
            return False
        return tokens[index].tokenType in cls.values

    def parse(self, tokens: tokenList, index: int, text: str) -> int:
        if not self.peek(tokens, index):
            raise lexer.InvalidToken("Expected a value", tokens[index], text)
        self.value = self.values[tokens[index].tokenType]()

        return self.value.parse(tokens, index, text)

    def operate(self, context: Context) -> int:
        return self.value.operate(context)


class UnaryRule(OperableRule):
    def __init__(self):
        self.value = ValueRule()

    @classmethod
    def peek(cls, tokens: tokenList, index: int) -> bool:
        return tokens[index].tokenType == lexer.SUB

    def parse(self, tokens: tokenList, index: int, text: str) -> int:
        lexer.assertTerminal("Expected '-'", lexer.SUB, tokens[index], text)
        return self.value.parse(tokens, index + 1, text) + 1

    def operate(self, context: Context) -> int:
        return -self.value.operate(context)


class ValRule(OperableRule):
    def __init__(self):
        self.value = None

    @classmethod
    def peek(cls, tokens: tokenList, index: int) -> bool:
        return UnaryRule.peek(tokens, index) or ValueRule.peek(tokens, index)

    def parse(self, tokens: tokenList, index: int, text: str) -> int:
        if UnaryRule.peek(tokens, index):
            self.value = UnaryRule()
        else:
            self.value = ValueRule()

        return self.value.parse(tokens, index, text)

    def operate(self, context: Context) -> int:
        return self.value.operate(context)


class StartRule(OperableRule):
    def __init__(self):
        self.value = ValRule()
        self.add = ComRule()

    @classmethod
    def peek(cls, tokens: tokenList, index: int) -> bool:
        return ValRule.peek(tokens, index)

    def parse(self, tokens: tokenList, index: int, text: str) -> int:
        size = self.value.parse(tokens, index, text)
        tmp = self.add.parse(tokens, index + size, text)
        if tmp == 0:
            self.add = None
        size += tmp
        return size

    def operate(self, context: Context):
        if self.add:
            return self.add.calculate(context, self.value.operate(context))
        return self.value.operate(context)


class Parser(OperableRule):
    def __init__(self, tokens: tokenList = None, raw: str = None):
        self.tokens = tokens or list()
        self.raw = raw or ""
        self.start = StartRule()
        self.results = list()

    def parseAll(self):
        self.start = StartRule()
        self.results = list()
        position = self.start.parse(self.tokens, 0, self.raw)
        while len(self.tokens) > position:
            self.results.append(ComRule())
            size = self.results[-1].parse(self.tokens, position, self.raw)
            if size == 0:
                raise lexer.InvalidToken(
                    "Expected Operator", self.tokens[position], self.raw
                )
            position += size

    @classmethod
    def peek(cls, tokens: tokenList, index: int) -> bool:
        return cls.start.peek(tokens, index)

    def parse(self, tokens: tokenList, index: int, text: str) -> int:
        self.start = StartRule()
        self.results = list()
        position = self.start.parse(tokens, index, text)
        while compareToken(tokens, index + position,
                           list(OperatorRule.operatorFunctions.keys())):
            self.results.append(ComRule())
            size = self.results[-1].parse(tokens, index + position, text)
            if size == 0:
                raise lexer.InvalidToken(
                    "Expected Operator", tokens[index + position], text
                )
            position += size
        return position

    def operate(self, context: Context) -> int:
        """
        Calculate the result of the parsed equation
        """
        result = self.start.operate(context)
        for group in self.results:
            result = group.calculate(context, result)
        return result
