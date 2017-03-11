from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from future.builtins import map

import random

from .clock import Clock
from .solution import SolutionTracker
from .state import State
from .tree import TreeNode
from .utils import INF, debug, info, warn


class Solver(object):

    TreeNode = TreeNode

    def __init__(self, root, pruning=None, rng_seed=None, rng_state=None, status_interval=1.0):
        if isinstance(root, State):
            root = type(self).TreeNode(root)
        if pruning is None:
            # Guess pruning by comparing the bound() method from the root state's class with the
            # bound() method from the base State class. If they're the same function object,
            # it means that the bound() method was not overridden and pruning will be disabled;
            # otherwise, the method was overridden and pruning will be enabled.
            pruning = type(root.state).bound is not State.bound
        info("Pruning is {}.".format("enabled" if pruning else "disabled"))
        if rng_seed is not None:
            info("Seeding RNG with {}...".format(rng_seed))
            random.seed(rng_seed)
        if rng_state is not None:
            rng_state_repr = "\n\t".join(map(str, rng_state))
            info("Setting RNG state to...\n\t{}".format(rng_state_repr))
            random.setstate(rng_state)

        self.root = root  # reference to the root node
        self.pruning = pruning  # pruning flag
        self.rng_seed = rng_seed  # seed for the random number generator
        self.rng_state = rng_state  # state for the random number generator
        self.status_interval = status_interval  # interval in seconds between status logs
        self.status_last = 0.0  # time of last status log
        self.cpu = Clock()  # tracks elapsed cpu time
        self.iters = 0  # number of completed iterations

        self.feas = SolutionTracker()  # solution tracker for feasible solutions
        self.feas.on_best.append(self._on_best_feas_sol)
        self.feas.on_worst.append(self._on_worst_feas_sol)
        self.infeas = SolutionTracker()  # solution tracker for infeasible solutions
        self.infeas.on_best.append(self._on_best_infeas_sol)
        self.infeas.on_worst.append(self._on_worst_infeas_sol)
        self.overall = SolutionTracker()  # solution tracker for all solutions
        self.overall.on_best.append(self._on_best_overall_sol)
        self.overall.on_worst.append(self._on_worst_overall_sol)

        # Set up event handlers that will propagate all .update() calls on the root node's
        # solution trackers to the solver's solution trackers.
        root.stats.feas.on_update.append(self.feas.update)
        root.stats.infeas.on_update.append(self.infeas.update)
        root.stats.overall.on_update.append(self.overall.update)

    def run(self, time_limit=INF, iter_limit=INF):
        info("Running with time_limit={} and iter_limit={}".format(time_limit, iter_limit))
        root = self.root
        cpu = self.cpu
        time_limit += cpu.elapsed  # convert rel time limit into abs limit
        iter_limit += self.iters  # convert rel iter limit into abs limit
        self._show_status(force=True)  # display status before entering main loop

        try:
            cpu.start()
            while cpu.elapsed < time_limit and self.iters < iter_limit and not root.is_exhausted:
                self._show_status()
                node = root.select()
                for child in node.expand(self.pruning):
                    assert child.parent is node
                    if child.state.is_terminal():
                        child.backpropagate(child.state.solution())
                        # Check if the child is still attached to our tree, because the
                        # backpropagation of its own solution may have triggered a pruning sweep
                        # which could possibly have deleted it.
                        if child.root is root:
                            child.delete()
                    else:
                        for sol in child.simulate():
                            child.backpropagate(sol)
                        assert child.stats.overall.count > 0
                self.iters += 1
        except KeyboardInterrupt:
            warn("Keyboard interrupt!")
        finally:
            cpu.stop()

        self._show_status(force=True)
        info("Search stopped.")
        if self.overall.count == 0:
            warn("Unable to find any solution.")
            return None
        if root.is_exhausted:
            info("Search tree exhausted.")
            if self.feas.count == 0:
                warn("Unable to find feasible solutions.")
            else:
                info("Solution is optimal.")
                self.overall.best.is_opt = True
        return self.overall.best

    def _show_status(self, force=False):
        now = self.cpu.elapsed
        if not force and now - self.status_last < self.status_interval:
            return
        self.status_last = now
        status = [
            "iter={:<6}  time={:<6.02f}  nodes={:<6}  |".format(
                self.iters, now, self.root.tree_size())
        ]
        if self.overall.count == 0:
            status.append("Search starting...")
        if self.feas.count > 0:
            status.append("feas[b={}, w={}, c={}/{} ({:.1f}%)]".format(
                self.feas.best.value, self.feas.worst.value,
                self.feas.count, self.overall.count,
                100 * self.feas.count / self.overall.count))
        if self.infeas.count > 0:
            status.append("infeas[b={}, w={}, c={}/{} ({:.1f}%)]".format(
                self.infeas.best.value.violation, self.infeas.worst.value.violation,
                self.infeas.count, self.overall.count,
                100 * self.infeas.count / self.overall.count))
        info("  ".join(status))

    def _on_best_feas_sol(self, old_sol, new_sol):
        debug("New best feasible solution: {} -> {}".format(old_sol.value, new_sol.value))

    def _on_worst_feas_sol(self, old_sol, new_sol):
        debug("New worst feasible solution: {} -> {}".format(old_sol.value, new_sol.value))

    def _on_best_infeas_sol(self, old_sol, new_sol):
        debug("New best infeasible solution: {} -> {}".format(old_sol.value, new_sol.value))

    def _on_worst_infeas_sol(self, old_sol, new_sol):
        debug("New worst infeasible solution: {} -> {}".format(old_sol.value, new_sol.value))

    def _on_best_overall_sol(self, old_sol, new_sol):
        info("New best overall solution: {} -> {}".format(old_sol.value, new_sol.value))
        new_sol.iteration = self.iters
        new_sol.time = self.cpu.elapsed
        if self.pruning and new_sol.is_feas:
            tree_size_before = self.root.tree_size()
            self.root.prune(cutoff=new_sol.value)
            tree_size_after = self.root.tree_size()
            info("Pruning removed {} nodes: {} -> {}".format(
                tree_size_before - tree_size_after, tree_size_before, tree_size_after))
        self._show_status(force=True)

    def _on_worst_overall_sol(self, old_sol, new_sol):
        debug("New worst overall solution: {} -> {}".format(old_sol.value, new_sol.value))
