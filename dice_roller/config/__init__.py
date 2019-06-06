import os
from os.path import dirname
import logging

from ruamel import yaml

from . import schemas


config_dir = dirname(dirname(dirname(__file__)))
__config_file = os.path.join(config_dir, 'config.yaml')
VERSION = 3

_logger = logging.getLogger(__name__)
_conf = dict()
config = schemas.Conf(_conf)


def merge(orig: dict, new: dict, delete=False, join=True):
    from collections import MutableMapping
    for k, v in orig.items():
        nv = new.get(k)
        # Merge the two values if they are also dicts
        if isinstance(v, MutableMapping) \
                and isinstance(nv, MutableMapping):
            merge(v, nv, delete)
            continue
        # set new value otherwise
        orig[k] = nv

    # Delete extraneous keys from the original
    if delete:
        deletes = set(orig) - set(new)
        for k in deletes:
            del orig[k]

    # Add extraneous keys from the new
    if join:
        joins = set(new) - set(orig)
        for k in joins:
            orig[k] = new[k]

    return orig


def print_errors(errors, msg):
    errs = list()
    for k, err in errors:
        errs.append("{}: {}".format(k, err))

    _logger.error("%s:\n\t%s",
                  msg, '\n\t'.join(errs))
    _logger.error("aborting save")


def save(file=None, delete=False):
    """
    Save the configuration file
    """
    _logger.info("Saving config file")

    global config
    schema = schemas.ConfSchema(strict=True)
    # Try to dump the schema to a dict, print any errors that occur
    try:
        data, errors = schema.dump(config)

        if errors:
            print_errors(errors, "Errors ocurred while saving config")
            return
    except Exception:
        _logger.exception("An exception ocurred while saving config")
        return

    # Merge the data with the loaded conf to preserve comments
    global _conf
    version = _conf['_conf']
    _conf = merge(_conf, data, delete=delete)
    # Make certain that the conf version is not removed
    _conf['_conf'] = version

    if file is None:
        file = __config_file

    # Write the yaml file
    with open(file, 'w', encoding='utf-8') as stream:
        yaml.round_trip_dump(_conf, stream)


def load(file=None):
    """
    Load the config file
    """
    _save = False
    _logger.info("Loading Configuration file")

    if file is None:
        file = __config_file

    # Read the file, if there is no file, use an empty dict
    global _conf
    if not os.path.exists(file):
        _conf = dict()
        _save = True
    else:
        with open(file, 'r', encoding='utf-8') as stream:
            _conf = yaml.round_trip_load(stream)

    if _conf is None:
        _conf = dict()
        _save = True

    # Migrate the config if the version is outdated
    version = _conf.get('_conf', -1)
    if version != VERSION:
        migrate(version)
        _conf['_conf'] = VERSION
        _save = True

    schema = schemas.ConfSchema(strict=True)
    # load the config object from the dictionary, print any errors that occur
    try:
        data, errors = schema.load(_conf)

        if errors:
            print_errors(errors, "Errors ocurred while loading config")
            return
    except Exception:
        _logger.exception("An exception ocurred while loading config")
        return

    global config
    config = data

    # save the config if a migration occurred
    if _save:
        save(file, delete=True)


def migrate(version):
    _logger.info("Migrating old config version from v.%d to %d",
                 version, VERSION)
    if version == -1:
        # There was no previous version, so there isn't anything we really can
        # do
        return

    if version == 1:
        # rename music to playlists
        _conf['playlists'] = _conf['music']
        del _conf['music']
        version = 2

    if version == 2:
        # Migration to Marshmallow
        # del voice, playlists
        try:
            del _conf['voice']
        except KeyError:
            pass
        try:
            del _conf['playlists']
        except KeyError:
            pass

        # move user_error to errors
        try:
            _conf['lines']['errors'] = _conf['lines']['user_error']
            del _conf['lines']['user_error']
        except KeyError:
            pass

        # convert on_rolls to new roll system
        rolls = _conf['lines'].get('on_roll', dict())
        new_rolls = list()
        for key, val in rolls.items():
            new_rolls.append(dict(
                values=[key],
                message=val
            ))
        _conf['lines']['on_roll'] = new_rolls

        version = 3


load()
