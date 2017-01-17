import random


class TreeNodeExpansion(object):
    """Lazy generator of child nodes.

    This object creates a copy of a given parent node and applies the next (unexpanded) branch in
    its branch list on demand. When the parent node has been completely expanded, the 'next()'
    method will return None and the 'is_finished' flag is set to true.
    """
    def __init__(self, node):
        self.node = node
        self.actions_iter = None
        self.actions_buff = None
        self.is_started = False
        self.is_finished = False

    def start(self):
        if self.is_started:
            raise ValueError("multiple attempts to start node expansion")
        self.actions_iter = iter(self.node.actions())
        self.is_started = True
        self._advance_branch()

    def next(self):
        if self.is_finished:
            raise ValueError("node expansion is already finished")
        child = self.node.copy()
        child.apply(self.actions_buff)
        self._advance_branch()
        return child

    def _advance_branch(self):
        try:
            self.actions_buff = next(self.actions_iter)
        except StopIteration:
            self.actions_buff = None
            self.is_finished = True
