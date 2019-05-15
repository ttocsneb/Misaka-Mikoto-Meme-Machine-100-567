import os
import sqlalchemy
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.exc import IntegrityError

import re

import alembic.config

from ..config import config, config_dir

from . import schema


alembic_ini = os.path.abspath(
    os.path.join(os.path.dirname(__file__), 'alembic'))


def _get_db_path():
    path = config.config.db_file
    if not os.path.isabs(path):
        return os.path.join(config_dir, path)
    return path


def upgrade():
    wd = os.getcwd()
    os.chdir(alembic_ini)

    # upgrade the database
    alembic_args = [
        'upgrade', 'head'
    ]
    alembic.config.main(argv=alembic_args)

    os.chdir(wd)


def get_one_or_create(session,
                      model,
                      create_method='',
                      create_method_kwargs=None,
                      **kwargs):
    try:
        return session.query(model).filter_by(**kwargs).one(), False
    except NoResultFound:
        kwargs.update(create_method_kwargs or {})
        created = getattr(model, create_method, model)(**kwargs)
        try:
            session.add(created)
            session.flush()
            return created, True
        except IntegrityError:
            session.rollback()
            return session.query(model).filter_by(**kwargs).one(), False


class Database:

    _name_regex = re.compile(r"([\S]+(?=:)|(?<=:)[\d]+|[^:\s]+|(?<!\S)(?=:))")

    def __init__(self, uri):
        self._uri = uri

        upgrade()

        self._engine = sqlalchemy.create_engine(uri, echo=False)

        self._session = sqlalchemy.orm.sessionmaker(bind=self._engine)

    def createSession(self):
        return self._session()

    def getServer(self, session, server_id):
        return get_one_or_create(
            session, schema.Server,
            create_method_kwargs=dict(
                prefix=config.config.prefix
            ), id=int(server_id))

    def getUser(self, session, user_id):
        return get_one_or_create(
            session, schema.User,
            id=int(user_id)
        )

    @classmethod
    def get_from_string(cls, session, clss, string, user_id=None):
        name = re.findall(cls._name_regex, string)

        if len(name) > 1:
            # Get by the id
            try:
                obj = session.query(clss).filter(
                    clss.id == int(name[1])
                ).first()
                if obj is not None:
                    return obj
            except ValueError:
                pass

        # Try to get the object from the author
        if user_id is not None:
            obj = session.query(clss).filter(
                clss.creator_id == user_id,
                clss.name == name[0].lower()
            ).first()
            if obj is not None:
                return obj

        # Try to get any object with the name
        obj = session.query(clss).filter(
            clss.name == name[0].lower()
        ).first()

        return obj


database = Database(config.config.db_file)
