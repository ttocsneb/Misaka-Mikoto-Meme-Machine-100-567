import unittest

from dice_roller.util import variables


class TestVariableParser(unittest.TestCase):

    def test_splitter(self):
        self.assertListEqual(
            variables._split_variables('asdf'),
            ['asdf']
        )
        self.assertListEqual(
            variables._split_variables('asdf{qwerty}'),
            ['asdf', '{qwerty}']
        )
        self.assertListEqual(
            variables._split_variables('{qwerty}asdf'),
            ['{qwerty}', 'asdf']
        )
        self.assertListEqual(
            variables._split_variables('{qwerty}'),
            ['{qwerty}']
        )
        self.assertListEqual(
            variables._split_variables('asdf{qwerty{foobar}}foobar'),
            ['asdf', '{qwerty{foobar}}', 'foobar']
        )
        self.assertListEqual(
            variables._split_variables('{qwerty}{asdf}'),
            ['{qwerty}', '{asdf}']
        )

    def test_variables(self):
        self.assertEqual(
            variables.getVariables('asdf'),
            set()
        )
        self.assertEqual(
            variables.getVariables('asdf{qwerty}'),
            {'qwerty'}
        )
        self.assertEqual(
            variables.getVariables('{qwerty}asdf'),
            {'qwerty'}
        )
        self.assertEqual(
            variables.getVariables('{qwerty}asdf{qwerty}'),
            {'qwerty'}
        )
        self.assertEqual(
            variables.getVariables('{qwerty}{asdf}'),
            {'qwerty', 'asdf'}
        )
        self.assertEqual(
            variables.getVariables('{0}asdf'),
            {'0'}
        )
        self.assertEqual(
            variables.getVariables('{qwerty}'),
            {'qwerty'}
        )
        self.assertEqual(
            variables.getVariables('{qwerty?{foo}}asdf'),
            {'qwerty', 'foo'}
        )
        self.assertEqual(
            variables.getVariables('{qwerty?foo}asdf'),
            {'qwerty'}
        )
    
    def test_variable_setting(self):
        self.assertEqual(
            variables.setVariables('asdf', 'qwerty', foo='bar', asdf='jeff'),
            'asdf'
        )
        self.assertEqual(
            variables.setVariables('asdf{foo}', 'qwerty', foo='bar', asdf='jeff'),
            'asdfbar'
        )
        self.assertEqual(
            variables.setVariables('asdf{0}', 'qwerty', foo='bar', asdf='jeff'),
            'asdfqwerty'
        )
        self.assertEqual(
            variables.setVariables('asdf{1?foo}', 'qwerty', foo='bar', asdf='jeff'),
            'asdffoo'
        )
        self.assertEqual(
            variables.setVariables('asdf{bam?asdf}', 'qwerty', foo='bar', asdf='jeff'),
            'asdfasdf'
        )
        self.assertEqual(
            variables.setVariables('asdf{1?{foo}}', 'qwerty', foo='bar', asdf='jeff'),
            'asdfbar'
        )
        self.assertEqual(
            variables.setVariables('asdf{foo?{asdf}}', 'qwerty', foo='bar', asdf='jeff'),
            'asdfbar'
        )
        self.assertEqual(
            variables.setVariables('asdf{bam?{asdf}}', 'qwerty', foo='bar', asdf='jeff'),
            'asdfjeff'
        )
        self.assertRaises(
            IndexError,
            variables.setVariables, 'asdf{1}', 'qwerty', foo='bar', asdf='jeff'
        )
        self.assertRaises(
            KeyError,
            variables.setVariables, 'asdf{aaaa}', 'qwerty', foo='bar', asdf='jeff'
        )
