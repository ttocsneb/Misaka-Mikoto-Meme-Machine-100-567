import os
from os.path import dirname
import logging

from ruamel import yaml

__config_dir = dirname(dirname(__file__))
__config_file = os.path.join(__config_dir, 'config.yaml')
VERSION = 2

_conf = dict()

_logger = logging.getLogger(__name__)


def save():
    """
    Save the config file
    """
    _logger.info("Saving config file..")

    res = yaml.round_trip_dump(_conf, indent=2, block_seq_indent=1)

    with open(__config_file, 'w', encoding='utf-8') as stream:
        stream.write(res)


def load():
    """
    Load the config file.
    """
    _logger.info("Loading Configuration file..")

    def load_defaults():
        global _conf
        _conf = get_defaults()
        save()

    if not os.path.exists(__config_file):
        load_defaults()
        return

    global _conf
    with open(__config_file, 'r', encoding='utf-8') as stream:
        _conf = yaml.round_trip_load(stream)
    
    if _conf is None:
        load_defaults()
        return
    
    version = _conf.get('_conf', -1)
    if version != VERSION:
        migrate(version)
        _conf['_conf'] = VERSION
        save()

    def mergeDict(old: dict, new: dict, layer=1) -> dict:
        """
        Merge a dictionary into another while prefering the old values over the new

        :param old: original dictionary
        :param new: new dictionary to merge
        """
        
        from collections import Mapping
        changed = False
        for key, val in new.items():
            # _logger.info("{} ({})".format(key, type(old.get(key))))
            if not key in old:
                _logger.debug("{}Adding new value {}".format('  ' * layer, key))
                changed = True
                old[key] = val
            elif issubclass(type(old[key]), Mapping) and issubclass(type(val), Mapping):
                _logger.debug("{}Merging dict {}".format('  ' * layer, key))
                changed = changed or mergeDict(old[key], val, layer + 1)

        return changed
    
    defaults = get_defaults()
    if mergeDict(_conf, defaults):
        save()


def get_defaults():
    defaults = dict()

    defaults['config'] = dict(
        voice=dict(
            opus='opus',
            default_volume=50
        ),
        prefix='!',
        description='I am a proffesional dice roller.  I use Random.org to roll my dice.\nMy source code is available at https://github.com/ttocsneb/discordDiceBot',
        token='Insert Token Here',
        random=dict(
            useRandomDotOrg=True,
            preFetchCount=30,
        ),
        mods=[],
        db_file=os.path.join(__config_dir, "db.dat")
    )

    defaults['lines'] = dict(
        crits=[u"Headshot!", u"Critical Hit!", u"Booyeah!", u"Crit!", u"Finish him!", u"Get pwn'd!"],
        critFails=[u"Oof", u"Fatality!", u"Ouch, ooch, oof your bones!", u"That'll hurt in the morning..."],
        dumb=[u"...What did you think would happen?", u"...Why?", u"Are you ok?",  u"Do you need a doctor?",
              u"What else did you think it would do?"],
        memes=[u"You.", u"I'm running out of memes...", u"This entire project.", u"Ay, aren't you a funny guy.",
               u"<Insert something cringy here>",u"tElL mE a mEmE!1!111!!1!!!!one!111!11", u"Are you feeling it now mr. crabs?",
               u"1v1 me on rust, howbou dah?"],
        startup=[u"*Yawn* Hello friends!", u"おはようございます!", u"おはよう、お父さん", u"Ohayō, otōsan!",
                 "Alright, who's ready to die?", u"Greetings humans.", u"My body is Reggie."],
        shutdown=[u"Bye!", u"Farewell comrades!", u"さようなら、お父さん!", u"Misaka doesn't wish to leave."],
        on_roll={
            '69': [u'Nice.'],
            '7': [u'Seben is my FABORIT number! But my faborit FABORIT number is seben BILLION!'],
            '77': [u'Seben is my FABORIT number! But my faborit FABORIT number is seben BILLION!'],
            '777': [u'Seben is my FABORIT number! But my faborit FABORIT number is seben BILLION!'],
            '7777': [u'Seben is my FABORIT number! But my faborit FABORIT number is seben BILLION!'],
            '420': [u'(insert bad weed joke here)', u'Quick! someone call the weed!']
        },
        user_error=dict(
            no_user=[u"You don't even have a character!", u"You aren't registered in the system."],
            no_char=[u"You don't have any characters!", u"Why would you try to do this when you don't even have a character?"],
            wrong_char=[u"It looks like we have a missing character.  Let's start a search party", u":wave: This isn't the character you are looking for."],
            too_many_char=[u"You have too many characters, specify your character next time.", u"Do you expect me to do all the work around here!  Tell me which character next time."]
        )
    )


    return defaults


def migrate(version):
    _logger.info("Migrating old config version from v{} to v{}..".format(version, VERSION))
    if version is -1:
        # There was no previous version, so there isn't anything we really can do
        return
    
    if version is 1:
        # rename music to playlists
        _conf['playlists'] = _conf['music']
        del _conf['music']
        version = 2

class SettingDict:

    def __init__(self, config):
        self._conf = config
    
    def __getitem__(self, index):
        return self._conf[index]
    
    def __setitem__(self, index, value):
        self._conf[index] = value
    
    def __contains__(self, value):
        return value in self._conf
    
    def __iter__(self):
        return iter(self._conf)
    
    def __len__(self):
        return len(self._conf)
    
    def get(self, value, default=None):
        try:
            return self[value]
        except KeyError:
            return default

class Conf(SettingDict):

    def __init__(self, config):
        super().__init__(config)
        self._conf = config
        self._lines = Lines(self._conf['lines'])
        self._config = Config(self._conf['config'])
    
    @property
    def config(self):
        return self._config
    
    @property
    def lines(self):
        return self._lines
    
    @property
    def playlists(self):
        return self._conf['playlists']


class Lines(SettingDict):

    def __init__(self, lines):
        super().__init__(lines)
        self._lines = lines
        self._user_error = UserError(self._lines['user_error'])
    
    @property
    def critFails(self):
        return self._lines['critFails']
    
    @property
    def shutdown(self):
        return self._lines['shutdown']
    
    @property
    def startup(self):
        return self._lines['startup']
    
    @property
    def dumb(self):
        return self._lines['dumb']
    
    @property
    def crits(self):
        return self._lines['crits']
    
    @property
    def memes(self):
        return self._lines['memes']
    
    @property
    def on_roll(self):
        return self._lines['on_roll']
    
    @property
    def user_error(self):
        return self._user_error


class UserError(SettingDict):

    def __init__(self, config):
        super().__init__(config)
        self._error = config
    
    @property
    def no_user(self):
        return self._error['no_user']
    
    @property
    def no_char(self):
        return self._error['no_char']
    
    @property
    def wrong_char(self):
        return self._error['wrong_char']
    
    @property
    def too_many_char(self):
        return self._error['too_many_char']


class Config(SettingDict):

    def __init__(self, config):
        super().__init__(config)
        self._config = config
        self._random = Random(self._config['random'])
    
    @property
    def prefix(self):
        return self._config['prefix']
    
    @property
    def token(self):
        return self._config['token']

    @property
    def random(self):
        return self._random

    @property
    def mods(self):
        return self._config['mods']
    
    @property
    def db_file(self):
        return self._config['db_file']
    
    @property
    def description(self):
        return self._config['description']


class Random(SettingDict):

    def __init__(self, random):
        super().__init__(random)
        self._random = random
    
    @property
    def useRandomDotOrg(self):
        return self._random['useRandomDotOrg']

    @property
    def preFetchCount(self):
        return self._random['preFetchCount']


# Load the config on import
load()

config = Conf(_conf)
