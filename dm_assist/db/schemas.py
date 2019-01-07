import collections
from marshmallow import Schema, fields, post_load

class User(object):
    def __init__(self, id, stats=None):
        self.id = id
        if stats is None:
            stats = dict()
        self.stats = stats
    
    @property
    def description(self):
        return "\n".join([key + ": " + stat for key, stat in self.stats.items()])
    
    def __repr__(self):
        return '<User(id={self.id})>'.format(self=self)


class Item(object):
    def __init__(self, name, id=None, equations=None, creator:User=None, desc=None, eq_desc=None):
        self.id = id
        self.name = name
        self.creator = creator
        self.desc = desc
        if eq_desc is None:
            eq_desc = dict()
        self.eq_desc = eq_desc
        if equations is None:
            equations = dict()
        self.equations = equations
    
    @property
    def short_desc(self):
        name = self.name.capitalize() + ':' + str(self.id)
        if self.desc is not None:
            name += ' ({})'.format(self.desc.capitalize())
        return name

    @property
    def description(self):
        equations = "\n".join(
            ["{}{}: {}".format(
                key,
                ' ({})'.format(self.eq_desc[key].capitalize()) if self.eq_desc.get(key) is not None else '',
                eq)
            for key, eq in self.equations.items()]
        )
        return "{}\n{}\n{}".format(self.short_desc, "-" * 10, equations)

    def __repr__(self):
        return '<Item(id={self.id},name={self.name})>'.format(self=self)


class Percentile(object):
    def __init__(self, weight:int, value):
        self.weight = int(max(1, weight))
        self.value = value


class Table(collections.Sequence):
    def __init__(self, name: str, id: int = None, desc = None, percentiles: list = list(), creator: User = None, hidden: bool = False):
        self.name = name
        self.id = id
        self.desc = desc
        if percentiles is None:
            percentiles = list()
        self.percentiles = percentiles
        self.creator = creator
        self.hidden = hidden
    
    def get_roll_sides(self):
        """
        Get the sides of dice that will be used for this table.

        Since the sides will almost allways be larger than the number of items,
        if a roll is larger than the size, then a reroll must be made.
        """

        # These are all values that 
        sides = (1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 24, 30, 40, 60, 100, 120)
        size = len(self)

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
        
        return '\n'.join(['{0: <{width}}: {1}'.format(*p, width=max_width) for p in percentile])
    
    def print_name(self):
        desc = ' ({})'.format(self.desc) if self.desc is not None else ''
        return '{}:{}'.format(self.name, self.id) + desc
    
    def __len__(self):
        return sum([p.weight for p in self.percentiles])

    def __getitem__(self, index):
        if index < 0:
            return self[len(self) - index]
        total = 0
        for i in self.percentiles:
            total += i.weight
            if index < total:
                return i
        raise IndexError
    
    def __iter__(self):
        return TableIterator(self)


class TableIterator(collections.Iterator):
    def __init__(self, table:Table):
        self.table = table
        self.index = 0
        self.total = 0
    
    def __next__(self):
        try:
            value = self.table.percentiles[self.index]
            if self.index >= self.total + value.weight:
                self.index += 1
                value = self.table.percentiles[self.index]
            return value
        except IndexError:
            raise StopIteration


class Server(object):
    def __init__(self, id, prefix, items=None, users=None, tables=None):
        self.id = id
        self.prefix = prefix

        if items is None:
            items = list()
        self.items = items
        
        if users is None:
            users = list()
        self.users = users

        if tables is None:
            tables = list()
        self.tables = tables
    
    def table(self, id):
        for table in self.tables:
            if table.id is id:
                return table
        raise KeyError

    def table_name(self, name):
        for table in self.tables:
            if table.name == name:
                return table
        raise KeyError
    
    def get_table(self, id, default=None):
        try:
            return self.table(id)
        except KeyError:
            return default
    
    def get_table_name(self, name, default=None):
        try:
            return self.table_name(name)
        except KeyError:
            return default

    def item(self, id):
        """
        Get an item with the id

        raises KeyError if no item with the id exists
        """
        for item in self.items:
            if item.id is id:
                return item
        raise KeyError
    
    def item_name(self, name):
        """
        Get an item with the name

        raises KeyError if no item with the id exists
        """
        for item in self.items:
            if item.name == name:
                return item
        raise KeyError
    
    def get_item_name(self, name, default=None):
        """
        Get an item with the name
        """
        try:
            return self.item_name(name)
        except KeyError:
            return default

    def get_item(self, id, default=None):
        """
        Get an item with the id
        """
        try:
            return self.item(id)
        except KeyError:
            return default
    
    def add_item(self, item: Item):
        """
        Add an item to the server.

        The id is automatically generated, so a blank id is allowed
        """
        # generate a new id for the item
    
        ids = [0]
        ids.extend([i.id for i in self.items])
        new_id = max(ids)
        item.id = new_id + 1

        self.items.append(item)
    
    def add_table(self, table: Table):
        """
        Add a table to the server

        The id is automatically generated
        """

        ids = [0] + [t.id for t in self.tables]
        table.id = max(ids) + 1

        self.tables.append(table)

    def user(self, id):
        """
        Get the user object from the given id

        raises KeyError if none exist
        """
        for user in self.users:
            if user.id == id:
                return user
        raise KeyError
    
    def get_user(self, id):
        """
        Get the user object from the given id

        If no user exists, a new user will be created and added to the database
        """
        try:
            return self.user(id)
        except KeyError:
            user = User(id)
            self.users.append(user)
            self.save()
            return user
    
    def add_user(self, user: User):
        """
        Try to add a user object to the server.

        If the user is already on the server, raise KeyError
        """
        if self.get_user(user.id) is not None:
            raise KeyError

        self.users.append(user)

    def save(self):
        from . import db
        db.dump(self.id)

    async def async_save(self):
        self.save

    def __repr__(self):
        return '<Server(id={self.id})>'.format(self=self)


class UserSchema(Schema):
    id = fields.Str()
    stats = fields.Dict()

    @post_load
    def make_user(self, data):
        return User(**data)


class ItemSchema(Schema):
    id = fields.Int()
    name = fields.Str()
    equations = fields.Dict()
    creator = fields.Nested(UserSchema, only=['id'])

    desc = fields.Str(allow_none=True)
    eq_desc = fields.Dict()

    @post_load
    def make_item(self, data):
        return Item(**data)


class PercSchema(Schema):
    weight = fields.Int()

    value = fields.Str()

    @post_load
    def make_Perc(self, data):
        return Percentile(**data)


class TableSchema(Schema):
    id = fields.Int()
    name = fields.Str()
    desc = fields.Str(allow_none=True)
    creator = fields.Nested(UserSchema, only=["id"])
    hidden = fields.Bool()

    percentiles = fields.Nested(PercSchema, many=True)

    @post_load
    def make_table(self, data):
        return Table(**data)


class ServerSchema(Schema):
    id = fields.Str()
    prefix = fields.Str()

    items = fields.Nested(ItemSchema, many=True)
    users = fields.Nested(UserSchema, many=True)
    tables = fields.Nested(TableSchema, many=True)

    @post_load
    def make_server(self, data):
        return Server(**data)
