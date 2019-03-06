from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy import inspect

import collections

Base = declarative_base()


class Stat(Base):
    __tablename__ = 'stats'

    id = Column(Integer(), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String())
    value = Column(String())

    def __repr__(self):
        return "'{}': '{}'".format(self.name, self.value)


class Stats(collections.MutableMapping):

    def __init__(self, user):
        self._user = user

    def __getitem__(self, key):
        for stat in self._user.stats:
            if stat.name == key:
                return stat
        raise KeyError
    
    def __setitem__(self, key, value):
        try:
            stat = self[key]
            stat.value = value
        except KeyError:
            data = inspect(self._user).session.query(Data).first()
            
            stat = Stat(id=data.getNewId())
            stat.name = key
            stat.value = value
            self._user.stats.append(stat)

            return stat

    def __len__(self):
        return len(self._user.stats)
    
    def __iter__(self):
        for stat in self._user.stats:
            yield stat.name
    
    def __delitem__(self, key):
        stat = self[key]
        self._user.stats.remove(stat)


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer(), primary_key=True)
    stats = relationship("Stat", order_by="Stat.name",
                         cascade="all, delete, delete-orphan")
    equations = relationship("Equation", back_populates='creator')
    tables = relationship("Table", back_populates='creator')

    def getStats(self):
        return Stats(self)

    def __repr__(self):
        return "<User(id='{}')>".format(self.id)


class Equation(Base):
    __tablename__ = 'equations'

    id = Column(Integer(), primary_key=True)
    name = Column(String())
    equation = Column(String())
    creator_id = Column(Integer, ForeignKey("users.id"))
    creator = relationship("User", back_populates='equations')
    params = Column(Integer())

    desc = Column(String())

    def printName(self):
        name = str(self.name) + ":" + str(self.id)
        if self.params > 0:
            name += "({})".format(", ".join([str(i) for i in range(self.params)]))
        if self.desc:
            name += ' (' + self.desc + ')'
        return name

    def __repr__(self):
        return "<Equation(name='%s', equation='%s')>" % (self.name, self.equation)


class Percentile(Base):
    __tablename__ = 'percs'

    id = Column(Integer(), primary_key=True)
    table_id = Column(Integer(), ForeignKey('tables.id'))
    index = Column(Integer())

    weight = Column(Integer())
    value = Column(String())

    def __repr__(self):
        return "<Percentile(weight={}, value='{}')>".format(self.weight, self.value)


class TableItems(collections.MutableSequence):

    def __init__(self, table):
        self._table = table

    def __len__(self):
        return sum([p.weight for p in self._table.percentiles])

    def __getitem__(self, index):
        # Process Slices
        if isinstance(index, slice):
            return [self[i] for i in range(*index.indices(len(self)))]
        # Process negative indecies
        if index < 0:
            return self[len(self) - index]
        
        # Get the item
        total = 0
        for i in self._table.percentiles:
            total += i.weight
            if index < total:
                return i
        raise IndexError
    
    def __iter__(self):
        index = 0
        total = 0
        while True:
            try:
                value = self._table.percentiles[self.index]
                if index >= total + value.weight:
                    index += 1
                    value = self._table.percentiles[index]
                yield value
            except IndexError:
                return
    
    def __setitem__(self, index, value):
        # Process Slices
        if isinstance(index, slice):
            o_start, o_stop, o_step = index.indices(len(self))
            start = self._table.percentiles.index(self[o_start])
            stop = self._table.percentiles.index(self[o_stop])
            self._table.percentiles[slice(start, stop, o_step)] = value
            return

        self._table.percentiles[self._table.percentiles.index(self[index])] = value

    def insert(self, index, value):
        self._table.percentiles.insert(self._table.percentiles.index(self[index]))
    
    def __delitem__(self, index):
        # Process Slices
        if isinstance(index, slice):
            o_start, o_stop, o_step = index.indices(len(self))
            start = self._table.percentiles.index(self[o_start])
            stop = self._table.percentiles.index(self[o_stop])
            del self._table.percentiles[slice(start, stop, o_step)]
            return

        self._table.percentiles.remove(self[index])


class Table(Base):
    __tablename__ = 'tables'

    id = Column(Integer(), primary_key=True)
    creator_id = Column(Integer(), ForeignKey('users.id'))
    creator = relationship("User", back_populates='tables')

    name = Column(String())
    desc = Column(String())
    hidden = Column(Boolean())

    percentiles = relationship("Percentile", order_by='Percentile.index',
                               collection_class=ordering_list('index'),
                               cascade="all, delete, delete-orphan")

    def getItems(self):
        return TableItems(self)

    def get_roll_sides(self):
        """
        Get the sides of dice that will be used for this table.

        Since the sides will almost allways be larger than the number of items,
        if a roll is larger than the size, then a reroll must be made.
        """

        items = self.getItems()

        # These are all values that 
        sides = (1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 24, 30, 40, 60, 100, 120)
        size = len(items)

        def iterate():
            for s in sides:
                yield s
            import itertools
            for i in itertools.count(start=3):
                yield 10 ** i

        for side in iterate():
            if size <= side:
                return side

    def print_all_percentiles(self):
        """
        Get a string of all the items in this table
        """
        total = 1

        percentile = list()

        max_width = 0

        for perc in self.percentiles:
            if perc.weight is 1:
                string = str(total)
            else:
                string = str(total) + "-" + str(total + perc.weight - 1)
            total += perc.weight
            percentile.append((string, perc.value))
            max_width = max(max_width, len(string))
        
        return ['{0: >{width}}  {1}'.format(*p, width=max_width) for p in percentile]

    def print_name(self):
        desc = ' ({})'.format(self.desc) if self.desc else ''
        return '{}:{}'.format(self.name, self.id) + desc

    def __repr__(self):
        return "<Table(name='{}', desc='{}')>".format(self.name, self.desc)


class Data(Base):
    __tablename__ = 'data'

    id = Column(Integer(), primary_key=True)

    prefix = Column(String(length=1))

    current_id = Column(Integer())

    def getNewId(self):
        self.current_id += 1
        return self.current_id

    def __repr__(self):
        return "<Data(prefix='{}')>".format(self.prefix)