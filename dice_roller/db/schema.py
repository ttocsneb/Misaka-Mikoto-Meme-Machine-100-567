from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import (Column, Integer, BigInteger, String, Boolean, Float,
                        ForeignKey)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy import Table as Tab
from sqlalchemy.orm.session import Session

from . import data_models

Base = declarative_base()


class Stat(Base):
    __tablename__ = 'stat'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("user.id"))
    server_id = Column(BigInteger, ForeignKey("server.id"))
    name = Column(String(16))
    value = Column(String(45))
    calc = Column(Float, nullable=True)
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
    server_id = Column(BigInteger, ForeignKey("server.id"))
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
    weight = Column(Integer, default=1)
    value = Column(String(64))

    def __repr__(self):
        return "<TableItem(value='{}')>".format(self.value)


class Table(Base):
    __tablename__ = 'table'
    id = Column(Integer, primary_key=True, autoincrement=True)
    creator_id = Column(BigInteger, ForeignKey("user.id"))
    server_id = Column(BigInteger, ForeignKey("server.id"))

    name = Column(String(16))
    desc = Column(String(32), nullable=True)
    hidden = Column(Boolean(), default=False)

    items_list = relationship(TableItem, order_by='TableItem.index',
                              collection_class=ordering_list('index'),
                              cascade="all, delete, delete, delete-orphan")

    items = property(lambda self: data_models.TableItems(self))

    def print_name(self):
        desc = ' *{}*'.format(self.desc) if self.desc else ''
        return '{}:{}'.format(self.name, self.id) + desc

    def print_all_percentiles(self):
        """
        Get a string of all the items in this table
        """
        total = 1

        percentile = list()

        max_width = 0

        for item in self.items:
            if item.weight == 1:
                string = str(total)
            else:
                string = str(total) + "-" + str(total + item.weight - 1)
            total += item.weight
            percentile.append((string, item.value))
            max_width = max(max_width, len(string))

        return ['{0: >{width}}.  {1}'.format(*i, width=max_width)
                for i in percentile]

    def get_roll_sides(self):
        """
        Get the sides of the dice that will be used for this table.

        Since the sides will almost allways be larger be larger than
        the number of items, if a roll is larger than the size, then
        a reroll must be made.
        """

        items = self.items

        sides = (1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 24, 30, 40, 60, 100, 120)
        size = items.size

        def iter_sides():
            for s in sides:
                yield s
            import itertools
            for i in itertools.count(start=3):
                yield 10 ** i

        for side in iter_sides():
            if size <= side:
                return side

    def __repr__(self):
        return "<Table(name='{}')>".format(self.name)


class Equation(Base):
    __tablename__ = 'equation'
    id = Column(Integer, primary_key=True, autoincrement=True)
    creator_id = Column(BigInteger, ForeignKey("user.id"))
    server_id = Column(BigInteger, ForeignKey("server.id"))

    name = Column(String(16))
    desc = Column(String(32), nullable=True)
    value = Column(String(45))
    params = Column(Integer, default=0)

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
    'server_user', Base.metadata,
    Column('server_id', BigInteger, ForeignKey('server.id')),
    Column('user_id', BigInteger, ForeignKey('user.id'))
)


class User(Base):
    __tablename__ = 'user'
    id = Column(BigInteger, primary_key=True)
    active_server_id = Column(BigInteger, ForeignKey("server.id"))
    active_server = relationship("Server", uselist=False,
                                 foreign_keys=[active_server_id])

    stats_list = relationship(Stat, order_by="Stat.name",
                              cascade="all, delete, delete-orphan")
    all_equations = relationship(Equation, backref='creator')
    tables = relationship(Table, backref='creator')

    all_stats = property(
        lambda self: data_models.Stats(self.stats_list)
    )

    @property
    def stats(self):
        session = Session.object_session(self)
        return data_models.Stats(session.query(Stat).filter(
            Stat.user_id == self.id,
            Stat.server_id == self.active_server_id
        ).order_by(Stat.name).all())

    @property
    def equations(self):
        # Get all the equations that are both owned by this user, and in the
        # current active server
        session = Session.object_session(self)
        return session.query(Equation).filter(
            Equation.creator_id==self.id,
            Equation.server_id==self.active_server_id
        ).order_by(Equation.name).all()

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
                import traceback
                traceback.print_exc()
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
    id = Column(BigInteger, primary_key=True)
    prefix = Column(String(1), default='?')
    auto_add_stats = Column(Boolean, default=True)
    mod_id = Column(BigInteger, nullable=True)

    @property
    def mod(self):
        raise NotImplementedError

    users = relationship(User, secondary=server_user_table, backref='servers')

    def __repr__(self):
        return "<Server(id='{}')>".format(self.id)
