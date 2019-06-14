import re
import math
import collections

from . import dice, BadEquation, variables
from .. import db


def isTrue(a):
    """
    Checks if a number is considered true
    """
    return a > 0


class FunctionDict(collections.Mapping):

    def __init__(self, *args, **kwargs):
        self.dict = dict(*args, **kwargs)
        self._func = None

    def setFunction(self, function):
        self._func = function

    def __getitem__(self, key):
        try:
            return self.dict[key]
        except KeyError:
            pass
        if self._func is not None:
            if callable(self._func):
                return self._func(key)
            else:
                return self._func[key]
        raise KeyError

    def __iter__(self):
        return iter(self.dict)

    def __len__(self):
        return len(self._func)

    def __str__(self):
        return '{{{}}}'.format(', '.join(
            '{}: {}'.format(i, v) for i, v in self.items()
        ))


class Calculator:
    """
    This parses textual equations, and calculates the result.

    If you want to add your own functions, all you need to do is to set
    its precedence in the precedence variable, set the number of operands
    needed if it has more or less than 2, and create the function as a lambda
    in the functions dict.

    """

    # Lower numbers mean a lower precedence (it is less important)
    precedence = FunctionDict({
        'true': 1, 'false': 1,
        '<': 1, '>': 1, '=': 1, '<>': 1, '<=': 1, '>=': 1, 'or': 1, 'and': 1,
        '+': 2, '-': 2,
        '*': 3, '/': 3,
        '^': 4, '%': 4,
        'round': 6, 'max': 6, 'min': 6, 'floor': 6, 'ceil': 6,
        'adv': 6, 'dis': 6, 'top': 6, 'bot': 6, 'if': 6,
        'd': 7,
    })

    # A function by default has 2 arguments, if it does not, list the number
    # required here.
    function_length = FunctionDict({
        'round': 1,
        'adv': 1,
        'dis': 1,
        'top': 3,
        'bot': 3,
        'floor': 1,
        'ceil': 1,
        'if': 3,
        'true': 0,
        'false': 0
    })

    # All the functions are defined here as lambdas.
    functions = FunctionDict({
        # Basic functions
        '+': lambda a, b: a + b,
        '-': lambda a, b: a - b,
        '*': lambda a, b: a * b,
        '/': lambda a, b: a / b,
        '^': lambda a, b: a ** b,
        '%': lambda a, b: a % b,

        # Boolean functions
        '<': lambda a, b: 1 if a < b else 0,
        '<=': lambda a, b: 1 if a <= b else 0,
        '>=': lambda a, b: 1 if a >= b else 0,
        '>': lambda a, b: 1 if a > b else 0,
        '<>': lambda a, b: 1 if a != b else 0,
        '=': lambda a, b: 1 if a == b else 0,
        'and': lambda a, b: 1 if isTrue(a) and isTrue(b) else 0,
        'or': lambda a, b: 1 if isTrue(a) or isTrue(b) else 0,
        'if': lambda a, b, c: b if isTrue(a) else c,

        # Advanced Functions
        'd': lambda a, b: dice.roll_sum(round(b), round(a))[0],
        'adv': lambda a: dice.roll_top(round(a), 1, 2),
        'dis': lambda a: dice.roll_top(round(a), 1, 2, False),
        'top': lambda a, b, c: dice.roll_top(round(b), round(c), round(a)),
        'bot': lambda a, b, c: dice.roll_top(round(b), round(c), round(a),
                                             False),
        'round': lambda a: round(a),
        'max': lambda a, b: max(a, b),
        'min': lambda a, b: min(a, b),
        'floor': lambda a: math.floor(a),
        'ceil': lambda a: math.ceil(a),

        # Constants
        'true': lambda: 1,
        'false': lambda: 0

    })

    def __init__(self):
        self._strip_regex = re.compile(r"\s+")
        self._parse_regex = re.compile(
            r"((^|(?<=[^\d)]))[-][\d.]+|[\d.]+|[a-z]+(:[\d]+)?|:[\d]+|[<>=]+|[\W])")
        self._check_vars_regex = re.compile(r"{(.*?)}")
        # _parse_regex info
        #
        # (^|(?<=[^\w)]))[-][\d.]+
        # Negative Number
        #   - (^|(?<=[^\w)]))
        #     Assert that the next token will be unary
        #   - [-]
        #     Catch operator
        #   - [\d.]+
        #     Catch Decimal number
        #
        # [\d.]+
        # Decimal Numbers
        #
        # [a-z]+(:[\d]+)?
        # Functions
        #
        # :[\d]+
        # Function ids
        #
        # [<>=]+
        # Boolean operators
        #
        # [\W]
        # Operators

    def _get_elements(self, string) -> list:
        """
        Parse the regex of an equation into a list of operands and operators.
        """
        stripped = re.sub(self._strip_regex, "", string.lower())
        equation = [r[0] for r in re.findall(self._parse_regex, stripped)]
        return equation

    def _load_equation(self, data: list) -> list:
        """
        Parse an equation to be calculated easier by a computer using the
        Shunting Yard Algorithm.

        A SYA equation looks like this:

        ```
        5 + 4 * 3 => 5 4 3 * +
        ```
        """
        stack = list()
        num_parens = 0

        equation = list()

        for i in data:
            try:
                number = float(i)
                equation.append(number)
            except ValueError:
                # If the item is not a number, it must be an operator
                # Check if the item is the end of a parenthesis
                if i == ')':
                    # If so, pop all the operands up to the accompanying
                    # parentheses
                    num_parens -= 1
                    while len(stack) > 0:
                        pop = stack.pop()
                        if pop == '(':
                            break
                        if pop != ',':
                            equation.append(pop)
                else:
                    if i == '(':
                        num_parens += 1
                    elif i == ',':  # commas are treated like paranthathese
                        broken = False
                        while len(stack) > 0:
                            peek = stack[-1]
                            if peek != '(':
                                stack.pop()
                            if peek == ',' or peek == '(':
                                broken = True
                                break
                            equation.append(peek)
                        if not broken:
                            raise BadEquation("Improper use of commas.")
                    else:
                        # If the precedence of the stack is greater than the
                        # current precedence, than pop until it's not
                        while len(stack) > 0 and self.__class__.precedence.get(
                                i, 0) <= self.__class__.precedence.get(
                                stack[-1], 0):
                            pop = stack.pop()
                            if pop == '(':
                                raise BadEquation("Mismatched parentheses.")
                            equation.append(pop)
                    # Add the operator to the stack
                    stack.append(i)

        if num_parens is not 0:
            raise BadEquation("Mismatched parentheses.")

        while len(stack) > 0:
            equation.append(stack.pop())

        return equation

    def _calculate_equation(self, equation: list) -> float:
        """
        calculate a Shunting Yard equation.
        """
        stack = list()

        for i in equation:
            if isinstance(i, float):
                stack.append(i)
            else:
                # Load the operands
                operands = list()
                for _ in range(self.__class__.function_length.get(i, 2)):
                    try:
                        operands.insert(0, stack.pop())
                    except IndexError:
                        raise BadEquation("Invalid number of operands")
                try:
                    # Process the function
                    stack.append(self.__class__.functions[i](*operands))
                except KeyError:
                    raise BadEquation("Invalid Function **{}**".format(i))
                except Exception as e:
                    raise BadEquation(str(e))

        if len(stack) is not 1:
            raise BadEquation("Invalid number of operands.")

        return stack.pop()

    def parse_args(self, equation, session, user, args=None):
        """
        Set all the arguments in the equation
        """
        if args is None:
            args = list()

        loop = 0
        stats = dict()
        for stat in user.stats.values():
            stats[str(stat)] = stat.getValue()

        while len(re.findall(self._check_vars_regex, equation)) > 0:
            loop += 1
            if loop >= 20:
                raise BadEquation("Too much recursion in the equation!")
            try:
                equation = variables.setVariables(equation, *args, **stats)
            except KeyError:
                from string import Formatter
                params = [fn for _, fn, _, _ in Formatter().parse(equation)
                          if fn is not None]

                missing_keys = list(set(params).difference(stats.keys()))

                raise BadEquation(
                    "Could not find the stats: "
                    + ', '.join(["**{}**".format(mk) for mk in missing_keys])
                )
            except IndexError:
                raise BadEquation(
                    "Not enough arguments given"
                )

        return equation

    def parse_equation(self, string: str, session=None, user=None,
                       _recursed=False, _repeats=None) -> float:
        """
        Parse a human readable equation.

        This supports the following operators:

        ```
        + - * / ^ % d ( ) round(x)
        ```

        Note: d is used for rolling dice where the firstoperand is the number
        of dice to roll, and the second is the number of faces.

        an example of an equation:

        ```
        ((5 * 4 + 3 / 6) % 6)d6 = 2d6
        ```

        If there is a formatting problem with the given equation, a BadEquation
        error will be thrown.

        The session parameter is optional, and is an instance of a server
        object. Using the session parameter allows the use of custom equations.
        """

        if _recursed > 20:
            raise BadEquation("Too much recursion in the equation!")

        # Add the custom equations to the equation list
        if session is not None:
            repeats = dict() if _repeats is None else _repeats

            def getEquation(eq_name):
                try:
                    return repeats[eq_name].params
                except KeyError:
                    pass
                if user is not None:
                    eq = db.database.get_from_string(
                        session, db.schema.Equation, eq_name,
                        user.active_server.id, user.id)
                    if eq is None:
                        raise KeyError
                    repeats[eq_name] = eq
                    return eq.params

            def getEquationFunction(eq_name):
                try:
                    eq = repeats[eq_name]
                except KeyError:
                    pass
                if user is not None:
                    eq = db.database.get_from_string(
                        session, db.schema.Equation, eq_name,
                        user.active_server.id, user.id)
                    if eq is None:
                        raise KeyError
                    repeats[eq_name] = eq

                return lambda *args: self.parse_equation(
                    self.parse_args(eq.value, session, user, args),
                    session,
                    user,
                    _recursed=_recursed + 1)

            def getEquationPrecedence(eq_name):
                try:
                    eq = repeats[eq_name]
                except KeyError:
                    pass
                if user is not None:
                    eq = db.database.get_from_string(
                        session, db.schema.Equation, eq_name,
                        user.active_server.id, user.id)
                    if eq is None:
                        raise KeyError
                    repeats[eq_name] = eq
                return 6

            self.__class__.functions.setFunction(getEquationFunction)
            if _recursed is False:
                self.__class__.function_length.setFunction(getEquation)
                self.__class__.precedence.setFunction(getEquationPrecedence)

        # parse the string into a list of operators and operands.
        equation = self._get_elements(string)

        # Parse the equation using the Shunting Yard Algorithm
        equation = self._load_equation(equation)

        # Find the answer to the equation
        value = self._calculate_equation(equation)

        # Reset the custom equations
        if _recursed is False:
            self.__class__.function_length.setFunction(None)
            self.__class__.functions.setFunction(None)
            self.__class__.precedence.setFunction(None)

        # Force the result into an int if it's an integer value
        return int(value) if value == int(value) else value
