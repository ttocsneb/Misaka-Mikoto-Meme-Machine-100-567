import os
import sqlalchemy

from ..config import config

from . import server, conf


class Database:

    def __init__(self, uri):
        self._uri = uri
        self._engine = sqlalchemy.create_engine(uri, echo=True)

        self._session = sqlalchemy.orm.sessionmaker(bind=self._engine)

    def createSession(self):
        return self._session()


class Server(Database):

    def __init__(self, uri, id, prefix='!'):
        super().__init__(uri)

        server.Base.metadata.create_all(self._engine)

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
        if user is None:
            # Add user to server database
            user = server.User(id=id)
            session.add(user)
            if commit:
                session.commit()
            
            # Add user to servers database
            servers = getServers()
            serve_session = servers.createSession()

            # Get the user, if it does not exist, create one
            serve_user = serve_session.query(conf.User).filter(conf.User.id==id).first()
            if serve_user is None:
                serve_user = conf.User(id=id)
            data = Server.getData(session)

            # Get the server, if it doesn't exist, create one (shouldn't happen though)
            serve = serve_session.query(conf.Server).filter(conf.Server.id==data.id).first()
            if serve is None:
                serve = conf.Server(id=data.id, prefix=data.prefix)

            # Add the user to the server.
            serve.users.append(serve_user)

            # Don't check if commit is true, as this is a new session.
            serve_session.commit()
        
        return user


class Servers(Database):
    def __init__(self, uri):
        super().__init__(uri)

        conf.Base.metadata.create_all(self._engine)

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


def getServers():
    return _servers
