INF = float("inf")


class Infeasible(object):
    """
    Infeasible objects can be compared with other objects (such as floats), but always compare as
    greater (*i.e.* worse in a minimization sense) than those objects. Among infeasible objects,
    they compare by value, meaning that they can be used to represent different degrees of
    infeasibility.

    To inform the MCTS framework that a solution is infeasible, set an :class:`Infeasible` object
    as the solution's ``value`` attribute, like so:

    .. code-block:: python

        class MyNode(mcts.TreeNode):
            # (...)

            def simulate(self):
                # (...)
                infeas = len(self.unassigned_vars)
                if infeas > 0:
                    return mcts.Solution(value=mcts.Infeasible(infeas))
                # (...)

            # (...)
    """
    def __init__(self, infeas=+INF):
        self.infeas = infeas

    def __str__(self):
        return "{}({})".format(type(self).__name__, self.infeas)

    def __repr__(self):
        return "<{} @{:x}>".format(self, id(self))

    def __eq__(self, obj):
        return isinstance(obj, Infeasible) and self.infeas == obj.infeas

    def __ne__(self, obj):
        return not isinstance(obj, Infeasible) or self.infeas != obj.infeas

    def __gt__(self, obj):
        return not isinstance(obj, Infeasible) or self.infeas > obj.infeas

    def __ge__(self, obj):
        return not isinstance(obj, Infeasible) or self.infeas >= obj.infeas

    def __lt__(self, obj):
        return isinstance(obj, Infeasible) and self.infeas < obj.infeas

    def __le__(self, obj):
        return isinstance(obj, Infeasible) and self.infeas <= obj.infeas
