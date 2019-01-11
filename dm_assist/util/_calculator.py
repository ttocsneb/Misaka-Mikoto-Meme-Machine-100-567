import re
import math

from . import dice, BadEquation

def isTrue(a):
    """
    Checks if a number is considered true
    """
    return a > 0


class Calculator:
    """
    This parses textual equations, and calculates the result.

    If you want to add your own functions, all you need to do is to set 
    its precidence in the precidence variable, set the number of operands
    needed if it has more or less than 2, and create the function as a lambda
    in the functions dict.

    """

    # Lower numbers mean a lower precidence (it is less important)
    precidence = {
        '<': 1, '>': 1, '=': 1, '<>': 1, '<=': 1, '>=': 1, 'or': 1, 'and': 1,
        '+': 2, '-': 2,
        '*': 3, '/': 3,
        '^':4, '%':4,
        'd': 5,
        'round': 6, 'max': 6, 'min': 6, 'floor': 6, 'ceil': 6,
        'adv': 6, 'dis': 6, 'top': 6, 'bot': 6, 'if': 6
    }
    
    # A function by default has 2 arguments, if it does not, list the number required here.
    function_length = {
        'round': 1,
        'adv': 1,
        'dis': 1,
        'top': 3,
        'bot': 3,
        'floor': 1,
        'ceil': 1,
        'if': 3
    }

    # All the functions are defined here as lambdas.
    functions = {
        # Basic functions
        '+': lambda a, b: a + b,
        '-': lambda a, b: a - b,
        '*': lambda a, b: a * b,
        '/': lambda a, b: a / b,
        '^': lambda a, b: a ** b,
        '%': lambda a, b: a % b,

        # Boolean functions
        '<':  lambda a, b: 1 if a < b else 0,
        '<=': lambda a, b: 1 if a <= b else 0,
        '>=': lambda a, b: 1 if a >= b else 0,
        '>':  lambda a, b: 1 if a > b else 0,
        '<>': lambda a, b: 1 if a != b else 0,
        '=':  lambda a, b: 1 if a == b else 0,
        'and': lambda a, b: 1 if isTrue(a) and isTrue(b) else 0,
        'or': lambda a, b: 1 if isTrue(a) or isTrue(b) else 0,
        'if': lambda a, b, c: b if isTrue(a) else c,

        # Advanced Functions
        'd': lambda a, b: dice.roll_sum(round(b), round(a))[0],
        'adv': lambda a: dice.roll_top(round(a), 1, 2),
        'dis': lambda a: dice.roll_top(round(a), 1, 2, False),
        'top': lambda a, b, c: dice.roll_top(round(b), round(c), round(a)),
        'bot': lambda a, b, c: dice.roll_top(round(b), round(c), round(a), False),
        'round': lambda a: round(a),
        'max': lambda a, b: max(a, b),
        'min': lambda a, b: min(a, b),
        'floor': lambda a: math.floor(a),
        'ceil': lambda a: math.floor(a)
    }

    def __init__(self):
        self._strip_regex = re.compile(r"\s+")
        self._parse_regex = re.compile(r"((^|(?<=[^\d)]))[-][\d.]+|[\d.]+|[a-z]+|[<>=]+|[\W])")
        # _parse_regex info
        # 
        # (^|(?<=[^\w)]))[-][\d.]+
        # Negative Numbers
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
        # [a-z]+
        # Functions
        # 
        # [<>=]+
        # Boolean operators
        # 
        # [\W]
        # Operators


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
            except ValueError:  # If the item is not a number, it must be an operator
                # Check if the item is the end of a paranthesis
                if i == ')':
                    # If so, pop all the operands up to the acompanying paranthesis
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
                        # If the precidence of the stack is greater than the current precidence, than pop until it's not
                        while len(stack) > 0 and self.__class__.precidence.get(i, 0) <= self.__class__.precidence.get(stack[-1], 0):
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
                try:
                    try:
                        # Load the operands
                        operands = list()
                        for _ in range(self.__class__.function_length.get(i, 2)):
                            operands.insert(0, stack.pop())

                        # Process the function
                        stack.append(self.__class__.functions[i](*operands))
                    except IndexError:
                        raise BadEquation("Unbalanced number of operators or operands.")
                except IndexError:
                    raise BadEquation("Invalid Operator '{}'.".format(i))
        
        if len(stack) is not 1:
            raise BadEquation("Invalid number of operands.")
        
        return stack.pop()

    def parse_equation(self, string: str) -> float:
        """
        Parse a human readable equation.

        This supports the following operators:

        ```
        + - * / ^ % d ( ) round(x)
        ```

        Note: d is used for rolling dice where the firstoperand is the number of dice
        to roll, and the second is the number of faces.
        
        an example of an equation:

        ```
        ((5 * 4 + 3 / 6) % 6)d6 = 2d6
        ```

        If there is a formatting problem with the given equation, a BadEquation error
        will be thrown.
        """
        # parse the string into a list of operators and operands.
        stripped = re.sub(self._strip_regex, "", string.lower())
        equation = [r[0] for r in re.findall(self._parse_regex, stripped)]

        # Parse the equation using the Shunting Yard Algorithm
        equation = self._load_equation(equation)

        # Find the answer to the equation
        value = self._calculate_equation(equation)

        # Force the result into an int if it's an integer value
        return int(value) if value == int(value) else value
