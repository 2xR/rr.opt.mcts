from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from math import log, sqrt

from .solution import SolutionTracker
from .utils import INF


class Stats(object):
    """Base class for node statistics.

    The Stats object is used in the selection and backpropagation steps of MCTS, and can be
    replaced for experimenting with different node statistics and backpropagation strategies.
    """

    def __init__(self, node):
        self.node = node  # reference to the TreeNode object
        self.sols = []  # list of Solutions obtained through simulations started from `node`
        self.feas = SolutionTracker()  # solution tracker for feasible solutions
        self.infeas = SolutionTracker()  # solution tracker for infeasible solutions
        self.overall = SolutionTracker()  # solution tracker for all solutions

    def __str__(self):
        descr = []
        if self.feas.count > 0:
            descr.append("feas[b={}, w={}, c={}/{} ({:.1f}%)]".format(
                self.feas.best.value, self.feas.worst.value,
                self.feas.count, self.overall.count,
                100 * self.feas.count / self.overall.count))
        if self.infeas.count > 0:
            descr.append("infeas[b={}, w={}, c={}/{} ({:.1f}%)]".format(
                self.infeas.best.value.violation, self.infeas.worst.value.violation,
                self.infeas.count, self.overall.count,
                100 * self.infeas.count / self.overall.count))
        return "{}({})".format(type(self).__name__, "  ".join(descr))

    def __repr__(self):
        return "<{} @{:x}>".format(self, id(self))

    def update(self, sol, origin):
        """Update stats by taking into account a new solution `sol` started from node `origin`."""
        if origin is self.node:
            self.sols.append(sol)
        (self.feas if sol.is_feas else self.infeas).update(sol)
        self.overall.update(sol)

    def refresh(self):
        """Force a recomputation of all stats (usually after removing nodes from the MCTS tree).

        Returns:
            A boolean indicating whether any stats have changed or not.
        """
        feas_sols = []
        infeas_sols = []
        overall_sols = []
        for child in self.node.children:
            feas_sols.extend(child.stats.feas.extrema)
            infeas_sols.extend(child.stats.infeas.extrema)
            overall_sols.extend(child.stats.overall.extrema)
        for sol in self.sols:
            (feas_sols if sol.is_feas else infeas_sols).append(sol)
            overall_sols.append(sol)
        # WARNING: do *not* use 'or' below because, due to boolean shortcurcuit evaluation,
        # some of the sub-expressions may not be evaluated.
        return any([
            self.feas.refresh(feas_sols),
            self.infeas.refresh(infeas_sols),
            self.overall.refresh(overall_sols),
        ])

    def depth_score(self):
        """A scoring term that gives preference to nodes closer to the root (promotes expansion)."""
        return 1.0 / (1.0 + self.node.depth)

    def opt_exploitation_score(self):
        """UTC exploitation term **adapted for optimization**."""
        parent_node = self.node.parent
        if parent_node is None:
            return 0.0
        parent_stats = parent_node.stats
        best_sol = self.overall.best
        if best_sol.is_feas:
            z_node = best_sol.value
            z_best = parent_stats.feas.best.value
            z_worst = parent_stats.feas.worst.value
            min_exploit = parent_stats.infeas.count / parent_stats.overall.count
            max_exploit = 1.0
        else:
            z_node = best_sol.value.violation
            z_best = parent_stats.infeas.best.value.violation
            z_worst = parent_stats.infeas.worst.value.violation
            min_exploit = 0.0
            max_exploit = parent_stats.infeas.count / (1 + parent_stats.overall.count)
        if z_best == z_worst:
            raw_exploit = 0.0
        else:
            raw_exploit = (z_worst - z_node) / (z_worst - z_best)
            assert 0.0 <= raw_exploit <= 1.0
        return min_exploit + raw_exploit * (max_exploit - min_exploit)

    def uct_exploration_score(self):
        """UCT exploration term (note: does not use an exploration coefficient)."""
        parent_node = self.node.parent
        return (
            INF if parent_node is None else
            sqrt(2.0 * log(parent_node.stats.overall.count) / self.overall.count)
        )
