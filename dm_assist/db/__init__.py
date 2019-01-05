import os
import json

import logging

from . import schemas

from ..config import config


class Db:
    
    def __init__(self):
        self.database = dict()
        self._logger = logging.getLogger(__name__)

    def _load(self, file):
        db = None
        with open(file, 'r') as f:
            db = json.load(f)
        db_name = os.path.splitext(os.path.basename(file))[0]

        schema = schemas.ServerSchema()
        data = schema.load(db)
        if len(data.errors) > 0:
            self._logger.error("Unhandled errors while loading database:")
            for error, err_msg in data.errors.items():
                self._logger.error("%s: %s", error, err_msg)
            self._logger.error("Aborting load of %s", file)
        else:
            self.database[db_name] = data.data
    
    def load(self, name):
        db_dir = config.config.db_file

        self._logger.info("Loading database: %s", name)

        self._load(os.path.join(db_dir, name + '.db'))

    def load_all(self):
        self.database = dict()
        db_dir = config.config.db_file

        self._logger.info("Loading all databases")
        
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)

        db_files = os.listdir(db_dir)

        for db in db_files:
            self._load(os.path.join(db_dir, db))
    
    def _dump(self, path, name):
        schema = schemas.ServerSchema()
        db = schema.dump(self.database[name])

        data = db.data

        with open(os.path.join(path, name + '.db'), 'w') as f:
            json.dump(data, f)
    
    def dump(self, name):
        db_dir = config.config.db_file

        self._logger.info("Dumping database: %s", name)

        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
        self._dump(db_dir, name)

    def dump_all(self):
        db_dir = config.config.db_file

        self._logger.info("Dumping all databases")

        if not os.path.exists(db_dir):
            os.makedirs(db_dir)

        for name in self.database.keys():
            self._dump(db_dir, name)


db = Db()
