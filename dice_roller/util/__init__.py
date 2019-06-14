import urllib.request
import urllib.parse
import os
import json


class BadEquation(Exception):
    pass


# dice needs to be setup first, as calculator depends on dice
from . import _dice
dice = _dice.Dice()


from . import _calculator
calculator = _calculator.Calculator()


def get_random_index(messages: list):
    return (messages[dice.roll(len(messages)) - 1])


def format_name(name: str) -> str:
    """
    Capitalize every word in the given string.
    For some reason capitalize only capitalizes the first letter.

    This capitalizes every word.
    """
    return ' '.join([w.capitalize() for w in name.split(' ')])


def read_uri(uri: str) -> str:
    """
    Read a file from either a url or a file uri
    """
    url = urllib.parse.urlsplit(uri)
    scheme = url[0]
    if 'file' in scheme:
        path = ''.join(url[1:3])
        if not os.path.isabs(path):
            from os.path import dirname as d
            path = os.path.join(d(d(d(__file__))), path)
        with open(path) as f:
            return f.read()
    else:
        req = urllib.request.Request(urllib.parse.urlunsplit(url))
        with urllib.request.urlopen(req) as f:
            return f.read().decode('utf-8')


def read_json_uri(uri: str):
    return json.loads(read_uri(uri))
