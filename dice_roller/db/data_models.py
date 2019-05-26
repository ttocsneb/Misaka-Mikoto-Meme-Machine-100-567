
import collections


class Stats(collections.MutableMapping):

    def __init__(self, user):
        self._user = user

    def __getitem__(self, key):
        for stat in self._user.stats_list:
            if stat.name == key:
                return stat
        raise KeyError

    def __setitem__(self, key, value):
        try:
            stat = self[key]
            stat.value = value
        except KeyError:
            from .schema import Stat
            stat = Stat()
            stat.name = key
            stat.value = value
            self._user.stats_list.append(stat)

    def __len__(self):
        return len(self._user.stats_list)

    def __iter__(self):
        for stat in self._user.stats_list:
            yield stat.name

    def __delitem__(self, key):
        stat = self[key]
        self._user.stats_list.remove(stat)

    def __str__(self):
        return "{" + ",".join(
            ["{}: {}".format(i.name, i.value)
             for i in self._user.stats_list
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
