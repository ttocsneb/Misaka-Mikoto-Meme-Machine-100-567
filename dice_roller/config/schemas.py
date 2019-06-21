from marshmallow import Schema, fields, post_load
import collections


class Random:
    def __init__(self, data):
        self.useRandomDotOrg = data.get('useRandomDotOrg', True)
        self.preFetchCount = data.get('preFetchCount', 30)


class Config:
    def __init__(self, data):
        self.prefix = data.get('prefix', '?')
        self.token = data.get('token', None)
        self.random = data.get('random', Random(dict()))
        self.mods = data.get('mods', [])
        self.db_file = data.get('db_file', 'sqlite:///db.sqlite')
        self.stat_config = data.get(
            'stat_config',
            'https://raw.githubusercontent.com/ttocsneb/ddb_config/master/ddbconf.json')
        self.description = data.get(
            'description',
            "I am a professional dice roller.  I use Random.org to roll my dice.\n"
            + "My source code is available at https://github.com/ttocsneb/discordDiceBot")


class Error:
    def __init__(self, data):
        self.no_user = data.get('no_user', [
            u"You don't even have a character!",
            u"You aren't registered in the system."
        ])
        self.no_char = data.get('no_char', [
            u"You don't have any characters!",
            u"Why would you try to do this when you don't even have a character?"
        ])
        self.wrong_char = data.get('wrong_char', [
            u"It looks like we have a missing character.  Let's start a search party",
            u":wave: This isn't the character you are looking for."
        ])
        self.too_many_char = data.get('too_many_char', [
            u"You have too many characters, specify your character next time.",
            u"Do you expect me to do all the work around here!  Tell me which character next time."
        ])


class Roll(collections.Container):
    def __init__(self, values, message):
        self.values = values
        self.message = message

    @staticmethod
    def _slice_to_range(slc):
        import sys

        def if_none(a, b):
            return b if a is None else a

        return range(if_none(slc.start, 0),
                     if_none(slc.stop, sys.maxsize),
                     if_none(slc.step, 1))

    def __contains__(self, x):
        for val in self.values:
            # Check if the value is in the range
            if isinstance(val, slice):
                if x in self._slice_to_range(val):
                    return True
            if x == val:
                return True
        return False


class OnRoll(collections.MutableSequence):
    def __init__(self, iterable=[]):
        self._values = list(iterable)

    def __getitem__(self, index):
        return self._values[index]

    def __setitem__(self, index, value):
        self._values[index] = value

    def __delitem__(self, index):
        del self._values

    def __len__(self):
        return len(self._values)

    def insert(self, index, value):
        self._values.insert(index, value)

    def get(self, key, default=None):
        """
        Get the first item in the list that contains the key

        default is returned if there are none found
        """
        for message in self._values:
            if key in message:
                return message.message[0]
        return default

    def getAll(self, key):
        """
        Get every item in the list that contains the key

        returns an empty list if there are none found
        """
        result = list()
        for message in self._values:
            if key in message:
                result.extend(message.message)
        return result

    def contains(self, key):
        return self.get(key) is not None


class Lines:
    def __init__(self, data):
        self.critFails = data.get('critFails', [
            u"Oof", u"Fatality!", u"Ouch, ooch, oof your bones!",
            u"That'll hurt in the morning..."
        ])
        self.shutdown = data.get('shutdown', [
            u"Bye!", u"Farewell comrades!", u"さようなら、お父さん!",
            u"Misaka doesn't wish to leave."
        ])
        self.startup = data.get('startup', [
            u"*Yawn* Hello friends!", u"おはようございます!",
            u"おはよう、お父さん", u"Ohayō, otōsan!",
            "Alright, who's ready to die?", u"Greetings humans.",
            u"My body is Reggie."
        ])
        self.dumb = data.get('dumb', [
            u"...What did you think would happen?", u"...Why?",
            u"Are you ok?",
            u"Do you need a doctor?",
            u"What else did you think it would do?"
        ])
        self.crits = data.get('crits', [
            u"Headshot!", u"Critical Hit!", u"Booyeah!", u"Crit!",
            u"Finish him!", u"Get pwn'd!"
        ])
        self.memes = data.get('memes', [
            u"You.", u"I'm running out of memes...",
            u"This entire project.",
            u"Ay, aren't you a funny guy.",
            u"<Insert something cringey here>",
            u"tElL mE a mEmE!1!111!!1!!!!one!111!11",
            u"Are you feeling it now mr. crabs?",
            u"1v1 me on rust, howbou dah?"
        ])
        self.on_roll = OnRoll(data.get('on_roll', [
            Roll([69], [
                u'Nice.'
            ]),
            Roll([7, 77, 777, 7777], [
                u'Seben is my FABORIT number! But my faborit FABORIT number is seben BILLION!'
            ]),
            Roll([420], [
                u'(insert bad weed joke here)',
                u'Quick! someone call the weed!'
            ])
        ]))
        self.errors = data.get('errors', Error(dict()))


class Conf:
    def __init__(self, data):
        self.config = data.get('config', Config(dict()))
        self.lines = data.get('lines', Lines(dict()))


# Schemas


class SliceField(fields.Field):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _serialize(self, value, attr, obj):
        if isinstance(value, slice):
            slices = [value.start, value.stop, value.step]
            return ':'.join([str(v) for v in slices if v is not None])
        if isinstance(value, int):
            return value
        return int(value)

    def _deserialize(self, value, attr, data):
        def to_int(val):
            if val:
                return int(val)
            return None

        if isinstance(value, str):
            if ':' in value:
                return slice(*map(to_int, value.split(':')))
        return int(value)


class RandomSchema(Schema):
    useRandomDotOrg = fields.Boolean()
    preFetchCount = fields.Integer()

    @post_load
    def loadRandom(self, data):
        return Random(data)


class ConfigSchema(Schema):
    prefix = fields.String()
    token = fields.String()
    random = fields.Nested(RandomSchema)
    mods = fields.List(fields.Integer())
    db_file = fields.String()
    description = fields.String()
    stat_config = fields.String()

    @post_load
    def loadConfig(self, data):
        return Config(data)


class ErrorSchema(Schema):
    no_user = fields.List(fields.String())
    no_char = fields.List(fields.String())
    wrong_char = fields.List(fields.String())
    too_many_char = fields.List(fields.String())

    @post_load
    def loadError(self, data):
        return Error(data)


class RollSchema(Schema):
    values = fields.List(SliceField(), allow_none=False)
    message = fields.List(fields.String(), allow_none=False)

    @post_load
    def loadRoll(self, data):
        return Roll(**data)


class LinesSchema(Schema):
    critFails = fields.List(fields.String())
    shutdown = fields.List(fields.String())
    startup = fields.List(fields.String())
    dumb = fields.List(fields.String())
    crits = fields.List(fields.String())
    memes = fields.List(fields.String())
    on_roll = fields.Nested(RollSchema, many=True)
    errors = fields.Nested(ErrorSchema)

    @post_load
    def loadLines(self, data):
        return Lines(data)


class ConfSchema(Schema):
    config = fields.Nested(ConfigSchema)
    lines = fields.Nested(LinesSchema)

    @post_load
    def loadConf(self, data):
        return Conf(data)
