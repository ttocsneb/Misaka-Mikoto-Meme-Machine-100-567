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
        equations = "\n".join([key + ": " + eq for key, eq in self.equations.items()])
        return "{}:{}\n{}\n{}".format(self.name.capitalize(), self.id, "-" * 10, equations)

    def __repr__(self):
        return '<Item(id={self.id},name={self.name})>'.format(self=self)


class Server(object):
    def __init__(self, id, prefix, items=None):
        self.id = id
        self.prefix = prefix

        if items is None:
            items = list()
        self.items = items
    
    def item(self, id):
        """
        Get an item with the id

        raises IndexError if no item with the id exists
        """
        for item in self.items:
            if item.id is id:
                return item
        raise KeyError
    
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
        new_id = max(0, [i.id for i in self.items])
        item.id = new_id + 1

        self.items.append(item)

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


class ServerSchema(Schema):
    id = fields.Str()
    prefix = fields.Str()

    items = fields.Nested(ItemSchema, many=True)

    @post_load
    def make_server(self, data):
        return Server(**data)
