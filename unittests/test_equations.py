import unittest

from dice_roller import util

# see https://docs.python.org/3.5/library/unittest.html for info on creating a
# testcase


class TestEquationParser(unittest.TestCase):

    def fail_on_success(self, roll):
        self.assertRaises(util.BadEquation, util.calculator.parse_equation,
                          roll)

    def test_die_parse(self):

        self.fail_on_success('aah')

        self.fail_on_success('xd5')

        util.calculator.parse_equation('5.4d1')

        self.fail_on_success('1d0')

    def test_math_parse(self):

        self.assertEqual(util.calculator.parse_equation('1 + 1'), 2)
        self.assertEqual(util.calculator.parse_equation('1 - 1'), 0)
        self.assertEqual(util.calculator.parse_equation('2 * 2'), 4)
        self.assertEqual(util.calculator.parse_equation('1 / 2'), 0.5)
        self.assertEqual(util.calculator.parse_equation('1 % 2'), 1)
        self.assertEqual(util.calculator.parse_equation('2 ^ 3'), 8)
        self.assertEqual(util.calculator.parse_equation('floor(1.5)'), 1)
        self.assertEqual(util.calculator.parse_equation('ceil(1.5)'), 2)
        self.assertEqual(util.calculator.parse_equation('round(1.5)'), 2)
        self.assertEqual(util.calculator.parse_equation('max(1, 2)'), 2)
        self.assertEqual(util.calculator.parse_equation('min(1, 2)'), 1)

    def test_logic(self):
        self.assertEqual(util.calculator.parse_equation('if(1, 5, 0)'), 5)
        self.assertEqual(util.calculator.parse_equation('if(0, 5, 0)'), 0)
        self.assertEqual(util.calculator.parse_equation('or(0, 0)'), 0)
        self.assertEqual(util.calculator.parse_equation('or(1, 0)'), 1)
        self.assertEqual(util.calculator.parse_equation('or(0, 1)'), 1)
        self.assertEqual(util.calculator.parse_equation('or(1, 1)'), 1)
        self.assertEqual(util.calculator.parse_equation('and(0, 0)'), 0)
        self.assertEqual(util.calculator.parse_equation('and(1, 0)'), 0)
        self.assertEqual(util.calculator.parse_equation('and(0, 1)'), 0)
        self.assertEqual(util.calculator.parse_equation('and(1, 1)'), 1)

    def test_inequality(self):
        self.assertEqual(util.calculator.parse_equation('2 > 1'), 1)
        self.assertEqual(util.calculator.parse_equation('1 > 2'), 0)
        self.assertEqual(util.calculator.parse_equation('2 > 2'), 0)
        self.assertEqual(util.calculator.parse_equation('1 < 2'), 1)
        self.assertEqual(util.calculator.parse_equation('2 < 1'), 0)
        self.assertEqual(util.calculator.parse_equation('2 < 2'), 0)
        self.assertEqual(util.calculator.parse_equation('1 = 2'), 0)
        self.assertEqual(util.calculator.parse_equation('2 = 1'), 0)
        self.assertEqual(util.calculator.parse_equation('2 = 2'), 1)
        self.assertEqual(util.calculator.parse_equation('1 <> 2'), 1)
        self.assertEqual(util.calculator.parse_equation('2 <> 1'), 1)
        self.assertEqual(util.calculator.parse_equation('2 <> 2'), 0)
        self.assertEqual(util.calculator.parse_equation('1 <= 2'), 1)
        self.assertEqual(util.calculator.parse_equation('2 <= 1'), 0)
        self.assertEqual(util.calculator.parse_equation('2 <= 2'), 1)
        self.assertEqual(util.calculator.parse_equation('1 >= 2'), 0)
        self.assertEqual(util.calculator.parse_equation('2 >= 1'), 1)
        self.assertEqual(util.calculator.parse_equation('2 >= 2'), 1)

    def test_complex_equations(self):
        self.assertEqual(util.calculator.parse_equation('(floor(5 * 4 + 3 / 6) % 6)'), 2)
        self.assertEqual(util.calculator.parse_equation('((5 * 4 + 3 / 6) % 6)'), 2.5)
