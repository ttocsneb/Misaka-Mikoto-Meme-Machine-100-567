from marshmallow import Schema, fields, post_load
from . import schema


class DictField(fields.Nested):
    def __init__(self, nested: fields.FieldABC, key_name="name",
                 value_name="value", *args, **kwargs):
        """
        nested: nested object
        key_name: key to put key in the deserialized object
        value_name: key to put value in if the value is not a dict
        """
        super().__init__(nested, many=True, *args, **kwargs)

        self._key = key_name
        self._val = value_name

    def _serialize(self, nested_obj, attr, obj):
        def extract_key(item: dict):
            key = item.pop(self._key)
            if len(item) == 1:
                try:
                    return key, item[self._val]
                except KeyError:
                    pass
            return key, item

        nested_list = super()._serialize(nested_obj, attr, obj)
        nested_dict = dict()
        for item in nested_list:
            key, item = extract_key(item)
            nested_dict[key] = item
        return nested_dict

    def _deserialize(self, value, attr, data):
        def insert_key(item, key):
            if isinstance(item, dict):
                item[self._key] = key
                return item
            else:
                return {self._val: item, self._key: key}
        raw_list = [insert_key(item, key) for key, item in value.items()]
        nested_list = super()._deserialize(raw_list, attr, data)
        return nested_list


class StatSchema(Schema):
    name = fields.String()
    group = fields.String()
    value = fields.String()

    @post_load
    def createStat(self, item):
        return schema.RollStat(**item)


class StatGroupField(fields.Nested):
    """
    A nested Stat group field

    Each stat is grouped by its group

    If the stat does not have a group, None is used as it's group
    """

    def __init__(self, *args, **kwargs):
        super().__init__(StatSchema, many=True, *args, **kwargs)

    def _serialize(self, nested_list, attr, obj):
        raw_list = super()._serialize(nested_list, attr, obj)
        nested_dict = dict()

        for item in raw_list:
            if item.group not in nested_dict:
                nested_dict[item.group] = dict()
            nested_dict[item.group][item.name] = item.value

        return nested_dict

    def _deserialize(self, value, attr, data):
        raw_list = list()
        for group, items in value.items():
            for name, value in items.items():
                raw_list.append(dict(
                    group=group,
                    name=name,
                    value=value
                ))
        return super()._deserialize(raw_list, attr, data)


class EquationSchema(Schema):
    name = fields.String()
    value = fields.String()
    desc = fields.String(required=False)

    @post_load
    def createEquation(self, item):
        return schema.Equation(**item)


class Configuration:
    def __init__(self, stats: list, equations: list):
        self.stats = stats
        self.equations = equations


class ConfigurationSchema(Schema):
    stats = StatGroupField()
    equations = DictField(EquationSchema, "name", "value")

    @post_load
    def CreateConfiguration(self, item):
        return Configuration(**item)
