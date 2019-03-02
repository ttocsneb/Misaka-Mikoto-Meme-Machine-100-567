from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Table, ForeignKey
from sqlalchemy.orm import relationship

Base = declarative_base()


association_table = Table('association', Base.metadata,
    Column('server_id', Integer(), ForeignKey('servers.id')),
    Column('user_id', Integer(), ForeignKey('users.id'))
)


class Server(Base):
    __tablename__ = 'servers'

    id = Column(Integer(), primary_key=True)
    prefix = Column(String(1))

    users = relationship("User", secondary=association_table,
                         backref='servers')

    def __repr__(self):
        return "<ServerConf(id={}, prefix='{}')>".format(self.id, self.prefix)


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer(), primary_key=True)

    servers = relationship("Server", secondary=association_table,
                           backref='users')
