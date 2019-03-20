import os
import sqlalchemy
import re

import alembic.config

from ..config import config

from . import server, conf


alembic_ini = os.path.abspath(
    os.path.join(os.path.dirname(__file__), 'alembic'))

print(alembic_ini)

class Database:

    def __init__(self, uri):
        self._uri = uri
        self._engine = sqlalchemy.create_engine(uri, echo=False)

        self._session = sqlalchemy.orm.sessionmaker(bind=self._engine)

    def createSession(self):
        return self._session()


class Server(Database):

    _name_regex = re.compile(r"([\S]+(?=:)|(?<=:)[\d]+|[^:\s]+|(?<!\S)(?=:))")

    def __init__(self, uri, id, prefix='!'):
        super().__init__(uri)

        wd = os.getcwd()
        os.chdir(alembic_ini)

        # upgrade the database
        alembic_args = [
            '-n', 'server',
            '-x', 'url={}'.format(uri),
            'upgrade', 'head'
        ]
        alembic.config.main(argv=alembic_args)

        os.chdir(wd)

        # Setup the data row
        session = self.createSession()
        if session.query(server.Data).count() is 0:
            data = server.Data(id=id, prefix=prefix, current_id=0)
            session.add(data)
            session.commit()

    @staticmethod
    def getData(session) -> server.Data:
        return session.query(server.Data).first()
    
    @staticmethod
    def getUser(session, id, commit=True) -> server.User:
        user = session.query(server.User).filter(server.User.id==id).first()

        servers = getServers()
        serve_session = servers.createSession()
        data = Server.getData(session)
        serve_user = serve_session.query(conf.User).filter(conf.User.id==id).first()

        if user is None:
            # Add user to server database
            user = server.User(id=id)
            session.add(user)
            if commit:
                session.commit()
        
        if serve_user is None:
            # Get the user, if it does not exist, create one
            serve_user = conf.User(id=id)

            # Get the server, if it doesn't exist, create one (shouldn't happen though)
            serve = serve_session.query(conf.Server).filter(conf.Server.id==data.id).first()
            if serve is None:
                serve = conf.Server(id=data.id, prefix=data.prefix)

            # Add the user to the server.
            serve.users.append(serve_user)
        
        # Set the active_server to the session's server id
        serve_user.active_server_id = data.id
        serve_session.commit()

        return user
    
    @classmethod
    def get_from_string(cls, session, clss, string, user_id=None):
        name = re.findall(cls._name_regex, string)

        if len(name) > 1:
            # Get by the id
            try:
                obj = session.query(clss).filter(
                    clss.id==int(name[1])
                ).first()
                if obj is not None:
                    return obj
            except ValueError:
                pass
        
        # Try to get the object from the author
        if user_id is not None:
            obj = session.query(clss).filter(
                clss.creator_id==user_id,
                clss.name==name[0].lower()
            ).first()
            if obj is not None:
                return obj
        
        # Try to get any object with the name
        obj = session.query(clss).filter(
            clss.name==name[0].lower()
        ).first()

        return obj


class Servers(Database):
    def __init__(self, uri):
        super().__init__(uri)

        wd = os.getcwd()
        os.chdir(alembic_ini)

        # upgrade the database
        alembic_args = [
            '-n', 'conf',
            '-x', 'url={}'.format(uri),
            'upgrade', 'head'
        ]
        alembic.config.main(argv=alembic_args)

        os.chdir(wd)

    @staticmethod
    def getServer(session, id, commit=True):
        server = session.query(conf.Server).filter(conf.Server.id==id).first()
        if server is None:
            server = conf.Server(id=id, prefix=config.config.prefix)
            session.add(server)
            if commit:
                session.commit()
            
            # Generate a server db file
            getDb(id)

        return session.query(conf.Server).filter(conf.Server.id==id).first()


if not os.path.exists(config.config.db_file):
    os.makedirs(config.config.db_file)
_servers = Servers('sqlite:///' + os.path.join(config.config.db_file, 'servers.db'))
_dbs = dict()


def getDb(id):
    global _dbs
    try:
        return _dbs[id]
    except KeyError:
        file = os.path.join(config.config.db_file, str(id) + '.db')
        db = Server('sqlite:///' + file, id, config.config.prefix)
        _dbs[id] = db

        # Add the new server to servers db
        session = _servers.createSession()
        if session.query(conf.Server).filter(conf.Server.id==id).count() is 0:
            server = conf.Server(id=id, prefix=config.config.prefix)
            session.add(server)
            session.commit()

        return db


def getDbFromCtx(ctx, conf_session=None):
    import discord
    if ctx.message.channel.type in [discord.ChannelType.private, discord.ChannelType.group]:
        if conf_session is None:
            conf_session = getServers().createSession()

        user = conf_session.query(conf.User).filter(
            conf.User.id==ctx.message.author.id
        ).first()

        if user is None or user.active_server_id is None:
            return None
        
        server = user.active_server
    else:
        # Duck typing at its finest
        server = ctx.message.server
    
    return getDb(server.id)


def getServers():
    return _servers
