import re

INVALID = -1
WHITESPACE = 0
NUMBER = 1
COMMA = 2
NAME = 3
L_PAREN = 4
R_PAREN = 5
DOLLAR = 6
ADD = 8
SUB = 9
DIV = 10
MUL = 11
MOD = 12
EXP = 13
DICE = 14
Q_MARK = 15
EQ = 16
NE = 17
LE = 18
GE = 19
L = 20
G = 21


def typeToStr(tokenType: int):
    if tokenType is WHITESPACE:
        return "whitespace"
    if tokenType is NUMBER:
        return "number"
    if tokenType is COMMA:
        return ','
    if tokenType is NAME:
        return 'name'
    if tokenType is L_PAREN:
        return '('
    if tokenType is R_PAREN:
        return ')'
    if tokenType is DOLLAR:
        return '$'
    if tokenType is ADD:
        return '+'
    if tokenType is SUB:
        return '-'
    if tokenType is DIV:
        return '/'
    if tokenType is MUL:
        return '*'
    if tokenType is MOD:
        return '%'
    if tokenType is EXP:
        return '^'
    if tokenType is DICE:
        return 'd'
    if tokenType is Q_MARK:
        return '?'
    if tokenType is EQ:
        return '='
    if tokenType is NE:
        return '<>'
    if tokenType is LE:
        return '<='
    if tokenType is GE:
        return '>='
    if tokenType is L:
        return '<'
    if tokenType is G:
        return '>'
    return 'invalid'


class Token:
    def __init__(self, tokenType: int, content: str, character: int = 0):
        self.tokenType = tokenType
        self.content = content
        self.character = character

    def __str__(self):
        return self.content

    def __repr__(self):
        return "Token<{}, \"{}\">".format(
            typeToStr(self.tokenType), self.content
        )


class InvalidToken(Exception):
    def __init__(self, msg: str, token: Token, text: str,
                 print_got: bool = True):
        self.msg = msg or "Invalid Token"
        self.token = token
        self.text = text
        self.print_got = print_got

    def __str__(self):
        pointer = (" " * self.token.character) + "^"
        got = "Got: '%s'" % self.token
        return "%s. %s\n%s\n%s" % (
            self.msg, got if self.print_got else "", self.text, pointer
        )


def assertTerminal(msg: str, expected: int, actual: Token, text: str,
                   print_got: bool = True):
    if isinstance(expected, list):
        if actual.tokenType not in expected:
            raise InvalidToken(msg, actual, text, print_got)
    else:
        if actual.tokenType != expected:
            raise InvalidToken(msg, actual, text, print_got)


class NumberRule:
    @classmethod
    def parse(cls, text) -> Token:
        match = re.match(r"^\d+", text)
        if match:
            return Token(NUMBER, match[0])


class SimpleRule:
    chars = {
        ',': COMMA,
        '(': L_PAREN,
        ')': R_PAREN,
        '$': DOLLAR,
        '+': ADD,
        '-': SUB,
        '/': DIV,
        '*': MUL,
        '%': MOD,
        '^': EXP,
        'd': DICE,
        '?': Q_MARK,
        '=': EQ,
        '<': L,
        '>': G
    }

    @classmethod
    def parse(cls, text) -> Token:
        char = text[0]
        if char in cls.chars:
            return Token(cls.chars[char], char)


class StringRule:
    strings = {
        '<>': NE,
        '<=': LE,
        '>=': GE
    }

    @classmethod
    def parse(cls, text: str) -> Token:
        for k, v in cls.strings.items():
            if text.startswith(k):
                return Token(v, k)


class NameRule:
    @classmethod
    def parse(cls, text) -> Token:
        match = re.match(r"[^\s\-*/+<>=()$,%?]+", text)
        if match:
            return Token(NAME, match[0])


class WhitespaceRule:
    @staticmethod
    def parse(text) -> Token:
        match = re.match(r"^\s+", text)
        if match:
            return Token(WHITESPACE, match[0])


class Lexer:
    baseRules = [
        WhitespaceRule,
        StringRule,
        SimpleRule,
        NumberRule,
        NameRule
    ]

    def __init__(self, text, *rules):
        self.text = text
        self.rules = self.baseRules + list(rules)
        self.output = list()
        self.position = 0

    def parseNext(self) -> Token:
        for rule in self.rules:
            token = rule.parse(self.text[self.position:])
            if token:
                token.character = self.position
                self.position += len(token.content)
                self.output.append(token)
                return token
        token = Token(INVALID, self.text[0], self.position)
        self.position += 1
        self.output.append(token)
        return token

    def parseAll(self) -> list:
        while self.position < len(self.text):
            self.parseNext()
        return self.output

    def filterOut(self, *types) -> list:
        self.output = [i for i in self.output if i.tokenType not in types]
        return self.output

    def filterIn(self, *types) -> list:
        self.output = [i for i in self.output if i.tokenType in types]
        return self.output

    def getOutput(self) -> list:
        return self.output

    def getErrors(self, *errorTypes) -> list:
        errors = [
            InvalidToken("Invalid Token", i, self.text)
            for i in self.output if i.tokenType in errorTypes
        ]
        return errors
