from . import functions as functs
from collections import MutableMapping, Mapping

from typing import List, Dict


def parseString(text: str, context=None) -> int:
    """
    Parse and calculate a string as an equation using the provided context
    """
    from . import lexer, parser
    if not context:
        context = Context()
    lex = lexer.Lexer(text)
    lex.parseAll()
    lex.filterOut(lexer.WHITESPACE)

    par = parser.Parser(lex.getOutput(), text)
    par.parseAll()
    return par.operate(context)


class ConverterDict(Mapping):
    """
    A mapping that uses a function to convert each value in the mapping
    """
    def __init__(self, mapping: dict, conversion: callable):
        self._map = mapping
        self._con = conversion

    def __getitem__(self, key):
        return self._con(key, self._map[key])

    def __iter__(self):
        return iter(self._map)

    def __len__(self):
        return len(self._map)


class DynamicDict(MutableMapping):
    """
    Allows for Dynamic Dictionaries.

    A dynamic dictionary is a dictionary where the contents are unknown until
    it is viewed.

    This can hold multiple dictionaries that will be treated as a single
    dictionary. Because of this, it is technically possible to have multiple
    keys, but doing this can undefined behavior.
    """
    def __init__(self, *args, **kwargs):
        self._dynamics = [
            dict(*args, **kwargs)
        ]

    def add_dynamic(self, dynamic: dict):
        """
        Add a dictionary to the dynamic dictionary
        """
        self._dynamics.append(dynamic)

    def __get_dynamic(self, key) -> dict:
        for dyn in self._dynamics:
            if key in dyn:
                return dyn

    def __getitem__(self, key):
        for dyn in self._dynamics:
            try:
                return dyn[key]
            except KeyError:
                pass
        raise KeyError

    def __setitem__(self, key, value):
        dyn = self.__get_dynamic(key)
        if dyn is None:
            self._dynamics[0][key] = value
            return
        dyn[key] = value

    def __delitem__(self, key):
        dyn = self.__get_dynamic(key)
        if dyn is None:
            raise KeyError
        del dyn[key]

    def __iter__(self):
        for dyn in self._dynamics:
            for i in dyn:
                yield i

    def __len__(self):
        size = 0
        for dyn in self._dynamics:
            size += len(dyn)
        return size


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
        self.functions = DynamicDict()
        functs = self.default_functions

        if isinstance(functions, list):
            functs += functions
        elif isinstance(functions, dict):
            self.functions.update(functions)
        self.functions.update(dict((func.name, func) for func in functs))

        self.variables = DynamicDict()
        if variables:
            self.variables.update(variables)
