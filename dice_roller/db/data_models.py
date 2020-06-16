import re
import collections


class Stats(collections.MutableMapping):
    class Group(collections.MutableMapping):
        def __init__(self, user, group, group_name):
            self._user = user
            self._group = group
            self._group_name = group_name

        def __getitem__(self, key):
            return self._group[Stats.remove_specials(key)]

        def __setitem__(self, key, value):
            try:
                item = self[key]
                item.value = value
            except KeyError:
                from .schema import Stat
                stat = Stat()
                stat.name = Stats.remove_specials(key)
                stat.group = self._group_name
                stat.value = value
                stat.user_id = self._user.id
                stat.server_id = self._user.active_server_id
                self._group[stat.name] = stat
                self._user.stats_list.append(stat)

        def __len__(self):
            return len(self._group)

        def __iter__(self):
            return iter(self._group)

        def __delitem__(self, key):
            stat = self[key]
            self._user.stats_list.remove(stat)
            del self._group[Stats.remove_specials(key)]

        name = property(lambda self: self._group_name)

    group_regex = re.compile(r'(.+)\.(.+)')

    def __init__(self, user, stats):
        self._user = user
        self._stats = dict((str(x), x) for x in stats)
        self._groups = set(x.group for x in stats)

    @classmethod
    def remove_specials(cls, name):
        return ''.join(t for t in name.lower() if t.isalnum())

    @classmethod
    def parse_name(cls, name):
        try:
            group, name = re.findall(cls.group_regex, name)[0]
            group = cls.remove_specials(group)
            name = cls.remove_specials(name)
            return group, name
        except IndexError:
            return None, cls.remove_specials(name)

    @staticmethod
    def get_name(group, name):
        from .schema import Stat
        return Stat.get_name(group, name)

    def __getitem__(self, key):
        group, name = self.__class__.parse_name(key)
        return self._stats[self.get_name(group, name)]

    def __setitem__(self, key, value):
        try:
            stat = self[key]
            stat.value = value
        except KeyError:
            group, name = self.__class__.parse_name(key)
            from .schema import Stat
            stat = Stat()
            stat.name = name
            stat.group = group
            stat.value = value
            stat.user_id = self._user.id
            stat.server_id = self._user.active_server_id
            self._stats[str(stat)] = stat
            self._user.stats_list.append(stat)

    def __len__(self):
        return len(self._stats)

    def __iter__(self):
        return iter(self._stats)

    def __delitem__(self, key):
        stat = self[key]
        self._user.stats_list.remove(stat)
        group, name = self.__class__.parse_name(key)
        del self._stats[self.get_name(group, name)]

    def get_group(self, key):
        if key:
            group = self.__class__.remove_specials(key)
        else:
            group = key
        if group not in self._groups:
            raise KeyError
        items = collections.OrderedDict(
            sorted(
                (x.name, x) for x in self._stats.values() if x.group == group
            )
        )
        if items:
            return Stats.Group(self._user, items, group)
        raise KeyError

    def iter_groups(self):
        return iter(sorted(
            set(x.group for x in self._stats.values()),
            key=lambda x: (x or chr(0), x)
        ))

    def __str__(self):
        return "{" + ",".join(
            ["{}: {}".format(i, v)
             for i, v in self._stats.items()
             ]) + "}"


class TableItems(collections.MutableSequence):
    def __init__(self, table):
        self._table = table

    def __getitem__(self, index):
        return self._table.items_list[index]

    def __setitem__(self, index, value):
        from .schema import TableItem
        if isinstance(value, tuple):
            self._table.items_list[index] = TableItem(
                weight=value[0], value=value[1])
        elif isinstance(value, str):
            self._table.items_list[index] = TableItem(value=value)
        elif isinstance(value, TableItem):
            self._table.items_list[index] = value
        else:
            raise TypeError

    def __delitem__(self, index):
        del self._table.items_list[index]

    def __len__(self):
        return len(self._table.items_list)

    def insert(self, index, value):
        self._table.items_list.insert(index, value)

    @property
    def size(self):
        return sum([i.weight for i in self._table.items_list])

    def at(self, index):
        # Process Slices
        if isinstance(index, slice):
            return [self.at(i) for i in range(*index.indices(self.size))]
        # Process negative indices
        if index < 0:
            return self.at(self.size - index)

        # Get the item
        total = 0
        for i in self._table.items_list:
            total += i.weight
            if index < total:
                return i
        raise IndexError

    def put(self, index, value):
        self.insert(self.index(self.at(index)), value)

    def set(self, index, value):
        if isinstance(index, slice):
            o_start, o_stop, o_step = index.indices(self.size)
            start = self.index(self.at(o_start))
            stop = self.index(self.at(o_stop))
            self[slice(start, stop, o_step)] = value

        self[self.index(self.at(index))] = value

    def delete(self, index):
        if isinstance(index, slice):
            o_start, o_stop, o_step = index.indices(self.size)
            start = self.index(self.at(o_start))
            stop = self.index(self.at(o_stop))
            del self[slice(start, stop, o_step)]
            return

        self.remove(self.at(index))
