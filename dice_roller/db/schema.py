from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, Float, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy import Table as Tab

from . import data_models

Base = declarative_base()


class Stat(Base):
    __tablename__ = 'stat'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.id"))
    server_id = Column(Integer, ForeignKey("server.id"))
    name = Column(String(16))
    value = Column(String(45))
    calc = Column(Float)
    group = Column(String(16), nullable=True)

    def getValue(self):
        if self.calc is not None:
            return self.calc
        return self.value

    @property
    def fullname(self):
        if self.group is not None:
            return "{}.{}".format(self.group, self.name)
        return self.name

    def __repr__(self):
        return "<Stat(name='{}', value='{}')>".format(
            self.fullname, self.value)


class RollStat(Base):
    __tablename__ = 'rollstat'
    id = Column(Integer, primary_key=True, autoincrement=True)
    server_id = Column(Integer, ForeignKey("server.id"))
    name = Column(String(16))
    value = Column(String(45))
    group = Column(String(16), nullable=True)

    @property
    def fullname(self):
        if self.group is not None:
            return "{}.{}".format(self.group, self.name)
        return self.name

    def __repr__(self):
        return "<RollStat(name='{}', value='{}')>".format(
            self.fullname, self.value)


class TableItem(Base):
    __tablename__ = 'tableitem'
    id = Column(Integer, primary_key=True, autoincrement=True)
    table_id = Column(Integer, ForeignKey("table.id"))
    index = Column(Integer)
    weight = Column(Integer)
    value = Column(String(64))

    def __repr__(self):
        return "<TableItem(value='{}')>".format(self.value)


class Table(Base):
    __tablename__ = 'table'
    id = Column(Integer, primary_key=True, autoincrement=True)
    creator_id = Column(Integer, ForeignKey("user.id"))
    server_id = Column(Integer, ForeignKey("server.id"))

    name = Column(String(16))
    desc = Column(String(32))
    hidden = Column(Boolean())

    items_list = relationship(TableItem, order_by='TableItem.index',
                              collection_class=ordering_list('index'),
                              cascade="all, delete, delete, delete-orphan")

    items = property(lambda self: data_models.TableItems(self))

    def __repr__(self):
        return "<Table(name='{}')>".format(self.name)


class Equation(Base):
    __tablename__ = 'equation'
    id = Column(Integer, primary_key=True, autoincrement=True)
    creator_id = Column(Integer, ForeignKey("user.id"))
    server_id = Column(Integer, ForeignKey("server.id"))

    name = Column(String(16))
    desc = Column(String(32))
    value = Column(String(45))
    params = Column(Integer)

    def printName(self):
        name = str(self.name) + ":" + str(self.id)
        if self.params > 0:
            name += "(" + ", ".join(
                ["{" + str(i) + "}" for i in range(self.params)]
            ) + ")"
        if self.desc:
            name += " *" + self.desc + "*"
        return name

    def __repr__(self):
        return "<Equation(name='{}', value='{}')>".format(
            self.name, self.value)


server_user_table = Tab(
    'server-user', Base.metadata,
    Column('server_id', Integer, ForeignKey('server.id')),
    Column('user_id', Integer, ForeignKey('user.id'))
)


class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    active_server_id = Column(Integer, ForeignKey("server.id"), nullable=True)
    active_server = relationship("Server", uselist=False,
                                 foreign_keys=[active_server_id])

    stats_list = relationship(Stat, order_by="Stat.name",
                              cascade="all, delete, delete-orphan")
    equations = relationship(Equation, backref='creator')
    tables = relationship(Table, backref='creator')

    stats = property(
        lambda self: data_models.Stats(self)
    )

    def checkPermissions(self, ctx, obj_w_creator=None):
        """
        Check if the user has permission to do something

        This will return true if the user is a server/bot
        mod or has permission to change the server

        If obj_w_creator is present, this will return true
        if the user is the creator of the object
        """
        from ..config import config

        # Check if the user is the creator of the obj
        if obj_w_creator is not None:
            if ctx.message.author.id == str(obj_w_creator.creator_id):
                return True

        # Check if the user is a bot moderator
        if ctx.message.author.id in config.config.mods:
            return True

        member = self.getMember(ctx)
        if member is not None:
            try:
                # Check if the user has permission to change the server
                if member.server_permissions.manage_server:
                    return True

                # Check if the user is a server moderator for the bot
                if self.active_server.mod.id == self.id:
                    return True
            except:
                return False
        return False

    def getMember(self, ctx):
        """
        Get the member from the active server

        If the context is from the active server, then
        ctx.message.author will be returned
        """
        import discord

        if ctx.message.channel.type in [discord.ChannelType.private,
                                        discord.ChannelType.group]:
            # Get the active server object
            server = next((server for server in ctx.bot.servers
                           if server.id == str(self.active_server_id)
                           ), None)

            # Return the user object from the active server if it exists
            if server is not None:
                return next((user for user in server.users
                             if user.id == ctx.message.author.id
                             ), None)
            return None
        # If the context came from a standard server, than the author is
        # already a member of the active server
        return ctx.message.author

    def __repr__(self):
        return "<User(id='{}')>".format(self.id)


class Server(Base):
    __tablename__ = 'server'
    id = Column(Integer, primary_key=True)
    prefix = Column(String(1))
    auto_add_stats = Column(Boolean)
    mod_id = Column(Integer, ForeignKey("user.id"), nullable=True)

    @property
    def mod(self):
        raise NotImplementedError

    users = relationship(User, secondary=server_user_table, backref='servers')

    def __repr__(self):
        return "<Server(id='{}')>".format(self.id)
