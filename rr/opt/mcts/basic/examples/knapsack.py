from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from future.builtins import range

import collections
import random

import rr.opt.mcts.basic as mcts


Item = collections.namedtuple("Item", ["name", "value", "weight", "ratio"])


def new_item(name, value, weight):
    return Item(name, value, weight, value / weight)


def _build_instance(k, v, w, s):
    assert len(v) == len(w) == len(s)
    n = len(v)
    items = [new_item(i, v[i], w[i]) for i in range(n)]
    opt = {items[i] for i in range(n) if s[i] == 1}
    return items, k, opt


def instance_1():
    return _build_instance(
        k=165,
        v=[92, 57, 49, 68, 60, 43, 67, 84, 87, 72],
        w=[23, 31, 29, 44, 53, 38, 63, 85, 89, 82],
        s=[1, 1, 1, 1, 0, 1, 0, 0, 0, 0],
    )


def instance_2():
    return _build_instance(
        k=26,
        v=[24, 13, 23, 15, 16],
        w=[12, 7, 11, 8, 9],
        s=[0, 1, 1, 1, 0],
    )


def instance_8():
    return _build_instance(
        k=6404180,
        v=[825594, 1677009, 1676628, 1523970, 943972, 97426, 69666, 1296457,
           1679693, 1902996, 1844992, 1049289, 1252836, 1319836, 953277, 2067538,
           675367, 853655, 1826027, 65731, 901489, 577243, 466257, 369261],
        w=[382745, 799601, 909247, 729069, 467902, 44328, 34610, 698150,
           823460, 903959, 853665, 551830, 610856, 670702, 488960, 951111,
           323046, 446298, 931161, 31385, 496951, 264724, 224916, 169684],
        s=[1, 1, 0, 1, 1, 1, 0, 0, 0, 1, 1, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 1, 1, 1],
    )


def verify_instance(instance, *args, **kwargs):
    if isinstance(instance, (tuple, list)):
        items, capacity, optimum = instance
    elif callable(instance):
        items, capacity, optimum = instance()
    else:
        raise TypeError("unexpected instance value: {}".format(instance))
    mcts.config_logging(level="DEBUG")
    root = KnapsackTreeNode.root(items, capacity)
    sols = mcts.run(root, *args, **kwargs)
    assert set(sols.best.items_packed) == optimum
    assert root.is_exhausted


class KnapsackTreeNode(mcts.TreeNode):
    @classmethod
    def root(cls, items, capacity):
        root = cls()
        root.items_left = list(sorted(items, key=lambda i: i.ratio))
        root.items_packed = []
        root.capacity_required = sum(i.weight for i in items)
        root.capacity_left = capacity
        root.total_value = 0
        root.upper_bound = None
        return root

    def copy(self):
        clone = type(self)()
        clone.items_left = list(self.items_left)
        clone.items_packed = list(self.items_packed)
        clone.capacity_required = self.capacity_required
        clone.capacity_left = self.capacity_left
        clone.total_value = self.total_value
        clone.upper_bound = None
        return clone

    def branches(self):
        return (True, False) if len(self.items_left) > 0 else ()

    def apply(self, pack_item):
        item = self.items_left.pop()
        self.capacity_required -= item.weight
        if pack_item:
            self.items_packed.append(item)
            self.total_value += item.value
            self.capacity_left -= item.weight
            self.items_left = [i for i in self.items_left if i.weight <= self.capacity_left]
            self.capacity_required = sum(i.weight for i in self.items_left)

        if self.capacity_required <= self.capacity_left:
            self.total_value += sum(i.value for i in self.items_left)
            self.capacity_left -= sum(i.weight for i in self.items_left)
            self.capacity_required = 0
            self.items_packed.extend(self.items_left)
            self.items_left = []

    def simulate(self):
        node = self.copy()
        while len(node.items_left) > 0:
            node.apply(random.choice([True, False]))  # monte carlo simulation
        sol = mcts.Solution(obj=(node.total_value * -1))  # flip objective function
        sol.items_packed = node.items_packed
        return sol

    def bound(self):
        if self.upper_bound is None:
            bound = self.total_value
            capacity = self.capacity_left
            for item in reversed(self.items_left):
                if item.weight <= capacity:
                    bound += item.value
                    capacity -= item.weight
                else:
                    bound += item.value * capacity / item.weight
                    break
            self.upper_bound = bound
        return self.upper_bound * -1  # flip bound


def main():
    for instance_fnc in [instance_1, instance_2, instance_8]:
        print("_" * 100)
        print(instance_fnc.__name__)
        verify_instance(instance_fnc)


if __name__ == "__main__":
    main()
