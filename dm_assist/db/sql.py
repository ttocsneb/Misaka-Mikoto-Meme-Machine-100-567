import sqlalchemy
from . import sql_schema

class Database:

    def __init__(self, uri):
        self._uri = uri
        self._engine = sqlalchemy.create_engine(uri, echo=True)

        sql_schema.Base.metadata.create_all(self._engine)

        self._session = sqlalchemy.orm.sessionmaker(bind=self._engine)

    def createSession(self):
        return self._session()