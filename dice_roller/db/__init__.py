import os
import sqlalchemy
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.exc import IntegrityError
import logging

import re

import alembic.config

from ..config import config, config_dir

from . import schema

logger = logging.getLogger(__name__)

alembic_ini = os.path.abspath(os.path.dirname(__file__))


def _get_db_path():
    path = config.config.db_file
    if not os.path.isabs(path):
        return os.path.join(config_dir, path)
    return path


def upgrade():
    logger.info("Upgrading database..")

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

        self._engine = sqlalchemy.create_engine(uri, echo=False)

        self._session = sqlalchemy.orm.sessionmaker(bind=self._engine)

    def createSession(self):
        return self._session()

    def getServer(self, session, server_id, commit=True, **kwargs):
        """
        Get the server. If the server doesn't exist, then a new one will be
        created.
        """
        server_kwargs = dict(prefix=config.config.prefix).update(kwargs)
        value = get_one_or_create(
            session, schema.Server,
            create_method_kwargs=server_kwargs,
            id=int(server_id)
        )

        if commit and value[1]:
            session.commit()
        return value

    def getUser(self, session, user_id, server_id, commit=True, **kwargs):
        """
        Get the User. If the user doesn't exist, then a new one will be
        created.
        """
        user_kwargs = dict(active_server_id=server_id).update(kwargs)
        value = get_one_or_create(
            session, schema.User,
            create_method_kwargs=user_kwargs,
            id=int(user_id)
        )

        if commit and value[1]:
            session.commit()
        return value

    def getServerFromCtx(self, session, ctx, commit=True):
        """
        Get the server from context

        If the message is from a private/group chat, the server will be taken
        from the user's active server.  If the user doesn't exist, None will be
        returned
        """
        import discord
        # If the context exists in a private/group chat
        if ctx.message.channel.type in [discord.ChannelType.private,
                                        discord.ChannelType.group]:
            # Get the user, then the active server.
            # If the user doesn't exist, then there is no active server
            user = session.query(schema.User).get(ctx.message.author.id)
            if user is None:
                return None, False
            return user.active_server, False
        # Get the server
        return self.getServer(session, ctx.message.server.id, commit)

    def getUserFromCtx(self, session, ctx, update_server=True, commit=True):
        """
        Get the user from context

        If the user hasn't been created yet, and are in a private/group chat,
        the user won't be created, and None will be returned
        """
        import discord

        # Get the active server id
        if ctx.message.channel.type in [
                discord.ChannelType.private,
                discord.ChannelType.group]:
            active_server = None
        else:
            active_server = int(ctx.message.server.id)

        # get/create the user
        user, new = self.getUser(session, ctx.message.author.id, active_server,
                                 False)

        # If the user was created, and no active server was found, cancel the
        # creation
        if active_server is None and new:
            session.rollback()
            return None, False
        elif update_server and active_server and not new:
            user.active_server, new = self.getServerFromCtx(
                session, ctx, commit=commit)

        if commit:
            session.commit()

        return user, new

    @classmethod
    def get_from_string(cls, session, clss, string, server_id, user_id=None):
        name = re.findall(cls._name_regex, string)

        if len(name) > 1:
            # Get by the id
            try:
                obj = session.query(clss).filter(
                    clss.id == int(name[1]),
                    clss.server_id == int(server_id)
                ).first()
                if obj is not None:
                    return obj
            except ValueError:
                pass

        # Try to get the object from the author
        if user_id is not None:
            obj = session.query(clss).filter(
                clss.creator_id == user_id,
                clss.name == name[0].lower(),
                clss.server_id == int(server_id)
            ).first()
            if obj is not None:
                return obj

        # Try to get any object with the name
        obj = session.query(clss).filter(
            clss.name == name[0].lower(),
            clss.server_id == int(server_id)
        ).first()

        return obj


database = Database(config.config.db_file)
