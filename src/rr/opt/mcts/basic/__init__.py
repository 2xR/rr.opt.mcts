from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from future.builtins import object

import pkgutil
import time
import random
import logging
import logging.config
from math import log, sqrt


__version__ = pkgutil.get_data(__name__, "VERSION").decode("utf-8").strip()
INF = float("inf")
logger = logging.getLogger(__name__)
debug = logger.debug
info = logger.info
warn = logger.warn


def run(root, time_limit=INF, iter_limit=INF, pruning=None,
        rng_seed=None, rng_state=None, log_iter_interval=1000):
    """
    Monte Carlo Tree Search for **minimization** problems. Objective functions (and bounds) for
    maximization problems must be multiplied by -1.
    """
    if pruning is None:  # guess pruning from root node's class (check if defines a bound() func)
        pruning = callable(type(root).bound)
    if rng_seed is not None:
        info("Seeding RNG with {}...".format(rng_seed))
        random.seed(rng_seed)
    if rng_state is not None:
        random.setstate(rng_state)
    info("RNG initial state is {}.".format(random.getstate()))
    info("Pruning is {}.".format("enabled" if pruning else "disabled"))

    t0 = time.clock()  # initial cpu time
    sols = Solutions()  # object used to keep track of our best/worst solutions
    sol = root.simulate()  # run simulation and
    root.backpropagate(sol)  # backpropagation on root node
    sols.update(sol)  # update solutions with root sol
    t = time.clock() - t0  # cpu time elapsed
    i = 0  # iteration count

    try:
        while i < iter_limit and t < time_limit:
            logger.log(
                level=logging.INFO if i % log_iter_interval == 0 else logging.DEBUG,
                msg="[i={:<5} t={:3.02f}] {}".format(i, t, sols),
            )
            node = root.select(sols)  # selection step
            if node is None:
                info("Search complete, solution is optimal")
                sols.best.is_opt = True
                break  # tree exhausted
            children = node.expand(pruning=pruning, cutoff=sols.best.obj)  # expansion step
            if len(children) == 0:
                node.delete()
            else:
                z0 = sols.best.obj
                for child in children:
                    sol = child.simulate()  # simulation step
                    child.backpropagate(sol)  # backpropagation step
                    sols.update(sol)
                # prune only once after all child solutions have been accounted for
                if pruning and sols.best.obj < z0:
                    ts0 = root.tree_size()
                    root.prune(sols.best.obj)
                    ts1 = root.tree_size()
                    info("Pruning removed {} nodes ({} => {})".format(ts0 - ts1, ts0, ts1))
            # update elapsed time and iteration counter
            t = time.clock() - t0
            i += 1
    except KeyboardInterrupt:
        info("Keyboard interrupt!")
    info("Finished at iter {} ({:.02f}s): {}".format(i, t, sols))
    return sols


class Infeasible(object):
    """
    Infeasible objects can be compared with other objects (such as floats), but always compare as
    greater (i.e. worse in a minimization sense) than those objects. Among infeasible objects,
    they compare by value, meaning that there can be different degrees of infeasibility.
    """
    def __init__(self, value=+INF):
        self.value = value

    def __str__(self):
        return "{}({})".format(type(self).__name__, self.value)

    def __repr__(self):
        return "<{} @{:x}>".format(self, id(self))

    def __eq__(self, obj):
        return isinstance(obj, Infeasible) and self.value == obj.value

    def __ne__(self, obj):
        return not isinstance(obj, Infeasible) or self.value != obj.value

    def __gt__(self, obj):
        return not isinstance(obj, Infeasible) or self.value > obj.value

    def __ge__(self, obj):
        return not isinstance(obj, Infeasible) or self.value >= obj.value

    def __lt__(self, obj):
        return isinstance(obj, Infeasible) and self.value < obj.value

    def __le__(self, obj):
        return isinstance(obj, Infeasible) and self.value <= obj.value


class Solution(object):
    """Base class for solution objects. The simulate() method of TreeNode objects should return
    a Solution object.
    """
    def __init__(self, obj, data=None):
        assert obj is not None
        self.obj = obj  # objective function value (may be an Infeasible object)
        self.data = data  # solution data
        self.is_infeas = isinstance(obj, Infeasible)  # infeasible solution flag
        self.is_feas = not self.is_infeas  # feasible solution flag
        self.is_opt = False  # optimal solution flag ("manually" set by run())

    def __str__(self):
        return "{}(obj={}{})".format(type(self).__name__, self.obj, "*" if self.is_opt else "")

    def __repr__(self):
        return "<{} @{:x}>".format(self, id(self))


class Solutions(object):
    """Simple auxiliary object whose only responsibility is to keep track of best and worst
    feasible and infeasible solutions, the best overall solution, and also a list of increasingly
    better solutions found during the search.
    """
    # Initial values for attributes of Solutions object.
    INIT_FEAS_BEST = Solution(obj=+INF, data="<initial best feas solution>")
    INIT_FEAS_WORST = Solution(obj=-INF, data="<initial worst feas solution>")
    INIT_INFEAS_BEST = Solution(obj=Infeasible(+INF), data="<initial best infeas solution>")
    INIT_INFEAS_WORST = Solution(obj=Infeasible(-INF), data="<initial worst infeas solution>")

    def __init__(self, *sols):
        self.list = []  # Solution list
        self.best = self.INIT_INFEAS_BEST  # best overall solution
        self.feas_best = self.INIT_FEAS_BEST  # best feasible solution
        self.feas_worst = self.INIT_FEAS_WORST  # worst feasible solution
        self.infeas_best = self.INIT_INFEAS_BEST  # best (least) infeasible solution
        self.infeas_worst = self.INIT_INFEAS_WORST  # worst (most) infeasible solution
        for sol in sols:
            self.update(sol)

    def __str__(self):
        attrs = ["feas_best", "feas_worst", "infeas_best", "infeas_worst"]
        descr = ", ".join("{}={}".format(attr, getattr(self, attr).obj) for attr in attrs)
        return "{}({})".format(type(self).__name__, descr)

    def __repr__(self):
        return "<{} @{:x}>".format(self, id(self))

    def update(self, sol):
        # Update best and worst feasible solutions
        if sol.is_feas:
            if sol.obj < self.feas_best.obj:
                debug("New best feasible solution: {} -> {}".format(self.feas_best, sol))
                self.feas_best = sol
            if sol.obj > self.feas_worst.obj:
                debug("New worst feasible solution: {} -> {}".format(self.feas_worst, sol))
                self.feas_worst = sol
        # Update best and worst infeasible solutions
        else:
            if sol.obj < self.infeas_best.obj:
                debug("New best infeasible solution: {} -> {}".format(self.infeas_best, sol))
                self.infeas_best = sol
            if sol.obj > self.infeas_worst.obj:
                debug("New worst infeasible solution: {} -> {}".format(self.infeas_worst, sol))
                self.infeas_worst = sol
        # Update best overall solution
        if sol.obj < self.best.obj:
            info("New best solution: {} -> {}".format(self.best, sol))
            self.best = sol
            self.list.append(sol)


class TreeNode(object):
    """Base class for tree nodes. Subclasses should define:
        - tree management methods - copy(); apply(); branches()
        - MCTS-related methods - simulate()
        - branch-and-bound methods - bound() [optional]
    """
    def __init__(self):
        self.path = []  # path from root down to, but excluding, 'self' (i.e. top-down ancestors)
        self.parent = None  # reference to parent node
        self.children = None  # list of child nodes (when expanded)
        self.sim_count = 0  # number of simulations in this subtree
        self.sim_sol = None  # solution of this node's own simulation
        self.sim_best = None  # best solution of simulations in this subtree

    @property
    def is_expanded(self):
        """The 'children' attribute only becomes a list when the expand() method is called."""
        return self.children is not None

    @property
    def is_exhausted(self):
        """A node is exhausted if all its children have been completely explored and removed."""
        return self.children is not None and len(self.children) == 0

    def tree_size(self):
        stack = [self]
        count = 1
        while len(stack) > 0:
            node = stack.pop()
            if node.is_expanded:
                count += len(node.children)
                stack.extend(node.children)
        return count

    def add_child(self, node):
        node.path = self.path + [self]
        node.parent = self
        self.children.append(node)

    def remove_child(self, node):
        node.path = []
        node.parent = None
        self.children.remove(node)

    # Tree management abstract methods
    def copy(self):
        """Create a node containing a copy of this node's state."""
        raise NotImplementedError()

    def apply(self, branch):
        """Mutate this node's state by applying one of the actions produced by branches()."""
        raise NotImplementedError()

    def branches(self):
        """Produce a list of possible actions that could be applied to this node's state in order
        to generate its children."""
        raise NotImplementedError()

    # MCTS-related methods
    def select(self, sols):
        """Pick the most favorable node for exploration.

        This method starts at the root and descends until a leaf is found. In each level the child
        to descend to is the one with the best selection score.
        """
        # Check if tree has been completely explored.
        if self.is_exhausted:
            return None
        # Go down the tree picking the best child at each step.
        node = self
        while node.is_expanded:
            children = node.children
            if len(children) == 1:
                node = children[0]
            else:
                cands = max_elems(children, key=lambda n: n.selection_score(sols))
                node = cands[0] if len(cands) == 1 else random.choice(cands)
        return node

    def selection_score(self, sols):
        """Selection score uses an adapted UTC formula to balance exploration and exploitation.

        See https://en.wikipedia.org/wiki/Monte_Carlo_tree_search. The exploitation term has been
        adapted to the optimization context, where there is no concept of win ratio.
        """
        if self.sim_best.is_feas:
            z_node = self.sim_best.obj
            z_best, z_worst = sols.feas_best.obj, sols.feas_worst.obj
            exploit_min, exploit_max = 0.5, 1.0  # TODO: remove hard-coded magic numbers
        else:
            z_node = self.sim_best.obj.value
            z_best, z_worst = sols.infeas_best.obj.value, sols.infeas_worst.obj.value
            exploit_min, exploit_max = 0.0, 0.25  # TODO: remove hard-coded magic numbers
        if z_best == z_worst:
            raw_exploit = 0.0
        else:
            raw_exploit = (z_worst - z_node) / (z_worst - z_best)
            assert 0.0 <= raw_exploit <= 1.0
        exploit = exploit_min + raw_exploit * (exploit_max - exploit_min)
        explore = sqrt(2.0 * log(self.parent.sim_count) / self.sim_count)
        return exploit + explore

    def expand(self, pruning, cutoff):
        """Generate and link all children of this node."""
        assert self.children is None
        self.children = []
        for branch in self.branches():
            child = self.copy()
            child.apply(branch)
            if pruning and child.bound() >= cutoff:
                continue
            self.add_child(child)
        return self.children

    def simulate(self):
        """Run a randomized simulation from this node to completion or infeasibility."""
        raise NotImplementedError()

    def backpropagate(self, sol):
        """Integrate the solution obtained by this node's simulation into its subtree.

        This updates sim_count and sim_best in all ancestor nodes.
        """
        assert self.sim_count == 0
        self.sim_count = 1
        self.sim_sol = sol
        self.sim_best = sol
        for ancestor in self.path:
            ancestor.sim_count += 1
            if ancestor.sim_best.obj > sol.obj:
                ancestor.sim_best = sol

    def delete(self):
        """Remove a leaf or an entire subtree from the search tree, updating its ancestors' stats.

        This method unlinks the node from its parent, and also removes its simulation result from
        all the nodes in its path, which is roughly equivalent to the opposite of backpropagate().
        Note that nodes in the path *must* be updated in bottom-up order.
        Note also that deletion of a node may trigger the deletion of its parent.
        """
        node = self
        while True:
            # Keep references to the path and parent since they'd be lost after remove_child().
            bottom_up_path = reversed(node.path)
            parent = node.parent
            # Unlink node from parent.
            if parent is not None:
                parent.remove_child(node)
            # Update sim_count and sim_best for all ancestor nodes (bottom-up order!).
            for ancestor in bottom_up_path:
                ancestor.sim_count -= node.sim_count
                if ancestor.sim_best is node.sim_best:
                    # New ancestor sim_best is the best of children's sim_best or its own sim_sol.
                    candidates = [child.sim_best for child in ancestor.children]
                    candidates.append(ancestor.sim_sol)
                    ancestor.sim_best = min(candidates, key=lambda s: s.obj)
            # Propagate deletion to parent if it exists and has become empty, otherwise stop.
            if parent is None or len(parent.children) > 0:
                break
            node = parent

    # Branch-and-bound/pruning- related methods
    def prune(self, cutoff):
        """Called on the root node to prune off nodes/subtrees which can no longer lead to a
        solution better than the best solution found so far.
        """
        stack = [self]
        while len(stack) > 0:
            node = stack.pop()
            if node.bound() >= cutoff:
                node.delete()
            elif node.is_expanded:
                stack.extend(node.children)

    bound = (
        "A bound() method shoud be defined in subclasses wanting to use pruning. By default, "
        "pruning will be automatically activated if the root node's class defines a callable "
        "named 'bound()'.\n\n"
        "The bound() method should compute a lower bound on the optimal objective function "
        "value in the subtree under self.\n\n"
        "NOTE: in the base TreeNode class, 'bound' is not defined as a regular abstract method "
        "like e.g. branches() because the mcts.run() function detects that the root node class "
        "defines a bound() method using 'callable(type(root).bound)'. This should work correctly "
        "across Python 2 & 3."
    )


def max_elems(iterable, key=None):
    """Find the elements in 'iterable' corresponding to the maximum values w.r.t. 'key'."""
    iterator = iter(iterable)
    try:
        elem = next(iterator)
    except StopIteration:
        raise ValueError("argument iterable must be non-empty")
    max_elems = [elem]
    max_key = elem if key is None else key(elem)
    for elem in iterator:
        curr_key = elem if key is None else key(elem)
        if curr_key > max_key:
            max_elems = [elem]
            max_key = curr_key
        elif curr_key == max_key:
            max_elems.append(elem)
    return max_elems


def config_logging(name=__name__, level="INFO"):
    logging.config.dictConfig({
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            },
        },
        'handlers': {
            'default': {
                'level': level,
                'formatter': 'standard',
                'class': 'logging.StreamHandler',
            },
        },
        'loggers': {
            name: {
                'handlers': ['default'],
                'level': level,
                'propagate': True,
            },
        }
    })
