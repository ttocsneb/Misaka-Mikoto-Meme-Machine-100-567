from marshmallow import Schema, fields, post_load


class Item(object):
    def __init__(self, name, id=None, equations=None):
        self.id = id
        self.name = name
        if equations is None:
            equations = dict()
        self.equations = equations
    
    @property
    def description(self):
        equations = "\n".join([str(key) + ": " + str(eq) for key, eq in self.equations.items()])
        return "{}:{}\n{}\n{}".format(self.name.capitalize(), self.id, "-" * 10, equations)
    
    @property
    def short_desc(self):
        return self.name.capitalize() + ':' + str(self.id)

    def __repr__(self):
        return '<Item(id={self.id},name={self.name})>'.format(self=self)


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


class Server(object):
    def __init__(self, id, prefix, items=None, users=None):
        self.id = id
        self.prefix = prefix

        if items is None:
            items = list()
        self.items = items
        
        if users is None:
            users = list()
        self.users = users
    
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


class ItemSchema(Schema):
    id = fields.Int()
    name = fields.Str()
    equations = fields.Dict()

    @post_load
    def make_item(self, data):
        return Item(**data)


class UserSchema(Schema):
    id = fields.Str()
    stats = fields.Dict()

    @post_load
    def make_user(self, data):
        return User(**data)


class ServerSchema(Schema):
    id = fields.Str()
    prefix = fields.Str()

    items = fields.Nested(ItemSchema, many=True)
    users = fields.Nested(UserSchema, many=True)

    @post_load
    def make_server(self, data):
        return Server(**data)
