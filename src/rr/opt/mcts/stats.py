from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from copy import deepcopy


class State(object):
    def copy(self):
        return deepcopy(self)

    def actions(self):
        raise NotImplementedError()

    def apply(self, action):
        raise NotImplementedError()

    def is_terminal(self):
        actions = iter(self.actions())
        return next(actions, UNDEFINED) is UNDEFINED


class TreeNode(object):
    pass


class TreeNodeExpansion(object):
    pass


class TreeNodeStats(object):
    def include(self, sol):
        pass

    def exclude(self, ):

bound
prune

select
expand
simulate
backpropagate
delete
