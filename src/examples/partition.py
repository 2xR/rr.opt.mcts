from math import log
from bisect import insort
from collections import defaultdict

import rr.opt.mcts.simple as mcts


JOIN = 0
SPLIT = 1


def load_instance(filepath):
    with open(filepath, "rt") as istream:
        return [int(line.strip()) for line in istream]


def objective(discrepancy):
    return log(abs(discrepancy)+1, 2)


def karmarkar_karp(labels):
    labels = list(labels)
    edges = []
    sum_remaining = sum(n for n, _ in labels)
    for _ in range(len(labels) - 1):
        n, i = labels.pop()
        m, j = labels.pop()
        insort(labels, (n-m, i))
        edges.append((i, j, SPLIT))
        sum_remaining -= 2 * m
    assert len(labels) == 1
    assert sum_remaining == labels[0][0]
    return edges, sum_remaining


class TreeNode(mcts.TreeNode):
    EXPANSION_LIMIT = float("inf")

    @classmethod
    def root(cls, instance):
        if isinstance(instance, str):
            instance = load_instance(instance)
        assert type(instance) is list  # NPP instances are flat lists of positive integers
        root = cls()
        root.labels = sorted((n, i) for i, n in enumerate(instance))  # vertex labels (nums)
        root.edges = []  # [(i, j, EDGE_TYPE<JOIN|SPLIT>)]
        root.sum_remaining = sum(instance)  # sum of all numbers still unassigned
        return root

    def copy(self):
        clone = mcts.TreeNode.copy(self)
        clone.labels = list(self.labels)
        clone.edges = list(self.edges)
        clone.sum_remaining = self.sum_remaining
        return clone

    def branches(self):
        # If there are only 4 or less items left, KK is optimal (and we've already done it in
        # simulate()). We only branch if the largest number does not exceed the sum of the other
        # items +1, and that was also already verified in the simulate() method.
        return () if len(self.labels) <= 4 else (SPLIT, JOIN)

    def apply(self, edge_type):
        labels = self.labels
        n, i = labels.pop()
        m, j = labels.pop()
        self.edges.append((i, j, edge_type))
        if edge_type == SPLIT:
            insort(labels, (n-m, i))
            self.sum_remaining -= 2 * m
        else:
            insort(labels, (n+m, i))

    def simulate(self):
        edges = self.edges
        if len(edges) > 0 and edges[-1][-1] == SPLIT:
            # reuse parent solution if this is the differencing child
            return self.parent.sim_sol
        labels = self.labels
        largest, i = labels[-1]
        delta = largest - (self.sum_remaining - largest)
        if delta >= -1:
            # the best solution in this subtree consists of putting the largest element in one
            # set and the remaining elements in the other
            labels.pop()
            for _, j in labels:
                edges.append((i, j, SPLIT))
            del labels[:]  # force next branches() call to return empty branch list
            return mcts.Solution(value=objective(delta), data=edges)
        else:
            kk_edges, diff = karmarkar_karp(self.labels)
            return mcts.Solution(value=objective(diff), data=edges+kk_edges)


def make_partition(edges):
    adj = {
        JOIN: defaultdict(set),
        SPLIT: defaultdict(set),
    }
    for i, j, edge_type in edges:
        adj_edge_type = adj[edge_type]
        adj_edge_type[i].add(j)
        adj_edge_type[j].add(i)
    nverts = len(edges) + 1
    subset = [None] * nverts
    _assign_subset(adj, subset, 0, 0)
    return subset


def _assign_subset(adj, subset, i, s):
    subset[i] = s
    for edge_type in (JOIN, SPLIT):
        adj_edge_type = adj[edge_type]
        adj_edge_type_i = adj_edge_type.pop(i, ())
        s_j = s if edge_type == JOIN else 1 - s
        for j in adj_edge_type_i:
            adj_edge_type[j].remove(i)
            _assign_subset(adj, subset, j, s_j)


mcts.config_logging()
r = TreeNode.root("instances/npp/hard1000.dat")
s = mcts.run(r, iter_limit=1000)
