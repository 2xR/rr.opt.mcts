from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from .infeasible import Infeasible
from .utils import INF


class Solution(object):
    """Base class for solution objects (normally it is not necessary to create a custom Solution
    subclass). The :meth:`simulate` method of :class:`TreeNode` objects should return a
    :class:`Solution` object. Solutions can have solution data attached, but this is optional.
    The solution's value, however, is required.
    """
    def __init__(self, value, data=None):
        assert value is not None
        self.value = value  # objective function value (may be an Infeasible object)
        self.data = data  # solution data
        self.is_infeas = isinstance(value, Infeasible)  # infeasible solution flag
        self.is_feas = not self.is_infeas  # feasible solution flag
        self.is_opt = False  # optimal solution flag (must be "manually" set)

    def __str__(self):
        return "{}(value={}{})".format(type(self).__name__, self.value, "*" if self.is_opt else "")

    def __repr__(self):
        return "<{} @{:x}>".format(self, id(self))


class SolutionTracker(object):
    """Simple auxiliary object whose only responsibility is to keep track of the best and worst
    solutions it has seen, as well as its number. It also provides a very basic implementation of
    the observer pattern, so that other objects may be notified when the best or worst solutions
    change.
    """

    # Initial values for attributes of SolutionTracker objects. These are set up in such a way
    # that they should always be replaced on the first call to update().
    INIT_BEST = Solution(value=Infeasible(+INF), data="<initial best solution>")
    INIT_WORST = Solution(value=-INF, data="<initial worst solution>")

    def __init__(self):
        cls = type(self)
        self.count = 0  # number of solutions seen
        self.best = cls.INIT_BEST  # best solution seen so far (through update())
        self.worst = cls.INIT_WORST  # worst solution seen so far (through update())
        self.on_best = []  # list of callables executed when best solution changes
        self.on_worst = []  # list of callables executed when worst solution changes
        self.on_update = []  # list of callables executed when update() is called

    def __str__(self):
        descr = "b={}, w={}, c={}".format(self.best.value, self.worst.value, self.count)
        return "{}({})".format(type(self).__name__, descr)

    def __repr__(self):
        return "<{} @{:x}>".format(self, id(self))

    @property
    def extrema(self):
        return (self.best, self.worst)

    def update(self, sol):
        self.count += 1
        best = self.best
        if sol.value < best.value:
            self.best = sol
            for handler in self.on_best:
                handler(best, sol)
        worst = self.worst
        if sol.value > worst.value:
            self.worst = sol
            for handler in self.on_worst:
                handler(worst, sol)
        for handler in self.on_update:
            handler(sol)

    def refresh(self, sols):
        """Recompute the best and worst solutions from `sols`, keeping the solution count intact.

        This is used when node stats need to be refreshed after some node is removed from the
        tree. The new best and worst solutions are computed only from those in `sols`, which is
        supposed to contain the solutions of the node and the best and worst solutions of the
        node's children.

        Returns:
            A boolean indicating if either the best or worst solutions have changed.
        """
        cls = type(self)
        old_best = self.best
        old_worst = self.worst
        new_best = cls.INIT_BEST
        new_worst = cls.INIT_WORST
        for sol in sols:
            if sol.value < new_best.value:
                new_best = sol
            if sol.value > new_worst.value:
                new_worst = sol
        self.best = new_best
        self.worst = new_worst
        return bool(
            new_best is not old_best or
            new_worst is not old_worst
        )
