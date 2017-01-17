import logging

from .solution import Solution
from .infeasible import Infeasible
from .misc import INF


class Solutions(object):
    """Simple auxiliary object whose only responsibility is to keep track of best and worst
    feasible and infeasible solutions, the best overall solution, and also a list of increasingly
    better solutions found during the search.
    """
    # Initial values for attributes of Solutions object.
    INIT_FEAS_BEST = Solution(value=+INF, data="<initial best feas solution>")
    INIT_FEAS_WORST = Solution(value=-INF, data="<initial worst feas solution>")
    INIT_INFEAS_BEST = Solution(value=Infeasible(+INF), data="<initial best infeas solution>")
    INIT_INFEAS_WORST = Solution(value=Infeasible(-INF), data="<initial worst infeas solution>")

    def __init__(self, *sols):
        self.list = []  # Solution list (only keeps solutions that improve upper bound)
        self.best = self.INIT_INFEAS_BEST  # best overall solution
        self.feas_count = 0  # number of feasible solutions seen
        self.feas_best = self.INIT_FEAS_BEST  # best feasible solution
        self.feas_worst = self.INIT_FEAS_WORST  # worst feasible solution
        self.infeas_count = 0  # number of infeasible solutions seen
        self.infeas_best = self.INIT_INFEAS_BEST  # best (least) infeasible solution
        self.infeas_worst = self.INIT_INFEAS_WORST  # worst (most) infeasible solution
        for sol in sols:
            self.update(sol)

    def __str__(self):
        attrs = ["feas_best", "feas_worst", "infeas_best", "infeas_worst"]
        descr = "feas_pct={:.0f}/{:.0f}, ".format(self.feas_pct, self.infeas_pct)
        descr += ", ".join("{}={}".format(attr, getattr(self, attr).value) for attr in attrs)
        return "{}({})".format(type(self).__name__, descr)

    def __repr__(self):
        return "<{} @{:x}>".format(self, id(self))

    @property
    def feas_ratio(self):
        return self.feas_count / (self.feas_count + self.infeas_count)

    @property
    def feas_pct(self):
        return self.feas_ratio * 100.0

    @property
    def infeas_ratio(self):
        return 1.0 - self.feas_ratio

    @property
    def infeas_pct(self):
        return self.infeas_ratio * 100.0

    def update(self, sol):
        # Update best and worst feasible solutions
        if sol.is_feas:
            self.feas_count += 1
            if sol.value < self.feas_best.value:
                debug("New best feasible solution: {} -> {}".format(self.feas_best, sol))
                self.feas_best = sol
            if sol.value > self.feas_worst.value:
                debug("New worst feasible solution: {} -> {}".format(self.feas_worst, sol))
                self.feas_worst = sol
        # Update best and worst infeasible solutions
        else:
            self.infeas_count += 1
            if sol.value < self.infeas_best.value:
                debug("New best infeasible solution: {} -> {}".format(self.infeas_best, sol))
                self.infeas_best = sol
            if sol.value > self.infeas_worst.value:
                debug("New worst infeasible solution: {} -> {}".format(self.infeas_worst, sol))
                self.infeas_worst = sol
        # Update best overall solution
        if sol.value < self.best.value:
            info("New best solution: {} -> {}".format(self.best, sol))
            self.best = sol
            self.list.append(sol)
