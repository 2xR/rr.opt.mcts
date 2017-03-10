from .utils import INF


class Infeasible(object):
    """Infeasible objects can be compared with other objects (such as floats), but always compare
    as greater (*i.e.* worse in a minimization sense) than those objects. Among infeasible
    objects, they compare by value (the `violation` attribute), meaning that they can be used to
    represent different degrees of infeasibility.

    To inform the MCTS framework that a solution is infeasible, set an :class:`Infeasible` object
    as the solution's `value` attribute, like so:

    .. code-block:: python

        class MyNode(mcts.TreeNode):
            # (...)

            def simulate(self):
                # (...)
                n_unassigned = len(self.unassigned_vars)
                if n_unassigned > 0:
                    return mcts.Solution(value=mcts.Infeasible(violation=n_unassigned))
                # (...)

            # (...)
    """

    __slots__ = ("violation",)

    def __init__(self, violation=+INF):
        self.violation = violation

    def __str__(self):
        return "{}({})".format(type(self).__name__, self.violation)

    def __repr__(self):
        return "<{} @{:x}>".format(self, id(self))

    def __float__(self):  # support conversion to float()
        return float(self.violation)

    def __eq__(self, obj):
        return isinstance(obj, Infeasible) and self.violation == obj.violation

    def __ne__(self, obj):
        return not isinstance(obj, Infeasible) or self.violation != obj.violation

    def __gt__(self, obj):
        return not isinstance(obj, Infeasible) or self.violation > obj.violation

    def __ge__(self, obj):
        return not isinstance(obj, Infeasible) or self.violation >= obj.violation

    def __lt__(self, obj):
        return isinstance(obj, Infeasible) and self.violation < obj.violation

    def __le__(self, obj):
        return isinstance(obj, Infeasible) and self.violation <= obj.violation
