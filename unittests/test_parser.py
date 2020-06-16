import unittest

from dice_roller import parser
from dice_roller.parser import lexer, functions as functs


class TestParser(unittest.TestCase):

    def test_addition(self):
        self.assertEqual(10, parser.parseString("5+5"))
        self.assertEqual(10, parser.parseString("5 + 5"))
        self.assertEqual(0, parser.parseString("5-5"))
        self.assertEqual(9, parser.parseString("5+2+2"))
        self.assertEqual(8, parser.parseString("5+4-1"))

    def test_comparison(self):
        self.assertEqual(1, parser.parseString("5=5"))
        self.assertEqual(0, parser.parseString("5=6"))
        self.assertEqual(1, parser.parseString("5<>6"))
        self.assertEqual(0, parser.parseString("5<>5"))
        self.assertEqual(1, parser.parseString("3<5"))
        self.assertEqual(0, parser.parseString("5<5"))
        self.assertEqual(1, parser.parseString("7>5"))
        self.assertEqual(0, parser.parseString("7>7"))
        self.assertEqual(1, parser.parseString("7>=5"))
        self.assertEqual(1, parser.parseString("5>=5"))
        self.assertEqual(0, parser.parseString("4>=5"))
        self.assertEqual(1, parser.parseString("3<=5"))
        self.assertEqual(1, parser.parseString("5<=5"))
        self.assertEqual(0, parser.parseString("6<=5"))

    def test_multiplication(self):
        self.assertEqual(4, parser.parseString("2*2"))
        self.assertEqual(2, parser.parseString("4/2"))
        self.assertEqual(2, parser.parseString("5/2"))
        self.assertEqual(1, parser.parseString("5%2"))

    def test_exponent(self):
        self.assertEqual(8, parser.parseString("2^3"))

    def test_variables(self):
        context = parser.Context(variables={"jeff": 5, "bar": 2})
        self.assertEqual(10, parser.parseString("$jeff*2", context))
        self.assertEqual(7, parser.parseString("$jeff+$bar", context))
        self.assertEqual(7, parser.parseString("$qwerty?$jeff+$bar", context))

    def test_args(self):
        context = parser.Context(args=[5, 3, 1])
        self.assertEqual(10, parser.parseString("$1*2", context))
        self.assertEqual(4, parser.parseString("$2+$3", context))
        self.assertEqual(4, parser.parseString("$4?$3+$2", context))

    def test_functions(self):
        self.assertEqual(3, parser.parseString("if(5=5,3,4)"))
        self.assertEqual(4, parser.parseString("if(5<>5,3,4)"))
        self.assertEqual(3, parser.parseString("if(5,3,4)"))
        self.assertEqual(3, parser.parseString("if(eq(5, 5, 5, 5),3,4)"))
        self.assertEqual(4, parser.parseString("if(eq(5, 4, 5, 5),3,4)"))
        self.assertEqual(1, parser.parseString("and(5=5,5<10,5>0)"))
        self.assertEqual(0, parser.parseString("and(6=5,6<10,6>0)"))
        self.assertEqual(1, parser.parseString("and(6, 4, 3)"))
        self.assertEqual(0, parser.parseString("and(5, 4, 3, 0)"))
        self.assertEqual(1, parser.parseString("or(6=5,6<10,6>0)"))
        self.assertEqual(0, parser.parseString("or(6=5,10<10,0>0)"))
        self.assertEqual(1, parser.parseString("or(5, 4, 3, 0)"))
        self.assertEqual(0, parser.parseString("or(0, 0, 0)"))
        self.assertEqual(1, parser.parseString("not(0)"))
        self.assertEqual(0, parser.parseString("not(1)"))
        self.assertEqual(0, parser.parseString("not(5)"))

    def test_customFunctions(self):
        context = parser.Context(functions=[
            functs.Function("bar", "5*5"),
            functs.Function("foo", "$1*5"),
            functs.Function("foobar", "bar() + foo(5)")
        ])

        self.assertEqual(25, parser.parseString("bar()", context))
        self.assertEqual(25, parser.parseString("foo(5)", context))
        self.assertEqual(10, parser.parseString("foo(2)", context))
        self.assertEqual(50, parser.parseString("foobar()", context))

    def test_parentheses(self):
        self.assertEqual(5, parser.parseString("(5)"))
        self.assertEqual(5, parser.parseString("((5))"))
        self.assertEqual(10, parser.parseString("((5)+5)"))
        self.assertEqual(21, parser.parseString("(5+2)*3"))

    def test_lexer(self):
        lex = lexer.Lexer("5+5")
        tokens = lex.parseAll()
        self.assertEqual(lexer.NUMBER, tokens[0].tokenType)
        self.assertEqual(lexer.ADD, tokens[1].tokenType)
        self.assertEqual(lexer.NUMBER, tokens[2].tokenType)

        self.assertRaises(lexer.InvalidToken, parser.parseString, "5++5")
        self.assertRaises(lexer.InvalidToken, parser.parseString, "5==5")
        self.assertRaises(lexer.InvalidToken, parser.parseString, "((5)+2))")
        self.assertRaises(lexer.InvalidToken, parser.parseString, "foobar")
        self.assertRaises(lexer.InvalidToken, parser.parseString, "$+")
        self.assertRaises(lexer.InvalidToken, parser.parseString, "*")
        self.assertRaises(lexer.InvalidToken, parser.parseString, "+5")
        self.assertRaises(lexer.InvalidToken, parser.parseString, "()")

    def test_all(self):
        context = parser.Context(args=[
            5,
            "5*2"
        ], functions=[
            functs.Function("bar", "5*5"),
            functs.Function("foo", "$1*5"),
            functs.Function("foobar", "bar() + foo(5)")
        ], variables={
            "bar": 3,
            "two": 2,
            "cheese": 14
        })

        self.assertEqual(
            14, parser.parseString("(bar() + 3) / (foo(1) - $bar)", context)
        )
        self.assertEqual(
            11, parser.parseString("$jeff?(($bar + 3) * $two) - 1", context)
        )
        self.assertEqual(
            1, parser.parseString("$cheese = -1 + 3 * 5", context)
        )
        self.assertEqual(
            1, parser.parseString("5 * 3 - 1 = $cheese", context)
        )
        self.assertEqual(
            36, parser.parseString("-$cheese + foobar()", context)
        )
        self.assertEqual(
            8, parser.parseString("5--3", context)
        )
        self.assertEqual(
            15, parser.parseString("(2^4-1)", context)
        )
