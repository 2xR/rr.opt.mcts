from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from future.builtins import object

import logging
import logging.config
import pkgutil
import random
import time
import types
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
    Monte Carlo Tree Search for **minimization** problems.

    Note:
        Objective functions (and bounds) for maximization problems must be multiplied by -1.

    Arguments:
        root (TreeNode): the root of the search tree.
        time_limit (float): maximum CPU time allowed.
        iter_limit (int): maximum number of iterations.
        pruning (bool or None): make the search use/not use pruning if true/false. If `None` is
            given (default), auto-detects pruning settings from root node.
        rng_seed: an object to pass to `random.seed()`. Does not seed the RNG if no value is given.
        rng_state: an RNG state tuple, as obtained from `random.getstate()`. Can be used to set a
            particular RNG state at the start of the search.
        log_iter_interval (int): interval, in number of iterations, between automatic log messages.

    Returns:
        `Solutions` object containing the best solution found by the search, as well as the list
        of incumbent solutions during the search.
    """
    if pruning is None:
        # Guess pruning by comparing the root node's bound() method with the bound() method from
        # the base TreeNode class.
        original_bound_meth = types.MethodType(TreeNode.bound, root)
        pruning = root.bound != original_bound_meth
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
            children = node.expand(pruning=pruning, cutoff=sols.best.value)  # expansion step
            if len(children) == 0:
                node.delete()
            else:
                z0 = sols.best.value
                for child in children:
                    sol = child.simulate()  # simulation step
                    child.backpropagate(sol)  # backpropagation step
                    sols.update(sol)
                # prune only once after all child solutions have been accounted for
                if pruning and sols.best.value < z0:
                    ts0 = root.tree_size()
                    root.prune(sols.best.value)
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


class Solution(object):
    """Base class for solution objects. The :meth:`simulate` method of :class:`TreeNode` objects
    should return a :class:`Solution` object. Solutions can have solution data attached, but this
    is optional. The solution's value, however, is required.
    """
    def __init__(self, value, data=None):
        assert value is not None
        self.value = value  # objective function value (may be an Infeasible object)
        self.data = data  # solution data
        self.is_infeas = isinstance(value, Infeasible)  # infeasible solution flag
        self.is_feas = not self.is_infeas  # feasible solution flag
        self.is_opt = False  # optimal solution flag ("manually" set by run())

    def __str__(self):
        return "{}(value={}{})".format(type(self).__name__, self.value, "*" if self.is_opt else "")

    def __repr__(self):
        return "<{} @{:x}>".format(self, id(self))


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
        descr = ", ".join("{}={}".format(attr, getattr(self, attr).value) for attr in attrs)
        return "{}({})".format(type(self).__name__, descr)

    def __repr__(self):
        return "<{} @{:x}>".format(self, id(self))

    def update(self, sol):
        # Update best and worst feasible solutions
        if sol.is_feas:
            if sol.value < self.feas_best.value:
                debug("New best feasible solution: {} -> {}".format(self.feas_best, sol))
                self.feas_best = sol
            if sol.value > self.feas_worst.value:
                debug("New worst feasible solution: {} -> {}".format(self.feas_worst, sol))
                self.feas_worst = sol
        # Update best and worst infeasible solutions
        else:
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


class TreeNode(object):
    """Base class for tree nodes. Subclasses should define:

    :tree management methods:
        - :meth:`root`
        - :meth:`copy`
        - :meth:`branches`
        - :meth:`apply`
    :MCTS-related methods:
        - :meth:`simulate`
    :branch-and-bound related methods:
        - :meth:`bound` *[optional]*
    """

    @classmethod
    def root(cls, instance):
        """Given a problem instance, create the root node for the associated search tree.

        Normally this method should create an empty node using ``root = cls()`` and then proceed
        to add the attributes necessary to fully represent a node in the tree.

        Parameters:
            instance: an object representing an instance of a specific problem. For example, for
                the knapsack problem, an instance would contain a list of item weights, a list of
                item values, and the knapsack's capacity. This could be a 3-tuple, a namedtuple,
                or even an instance of a custom class. The internal structure of the instance
                object is not dictated by the framework.

        Returns:
            TreeNode: the root of the search tree for the argument instance.
        """
        raise NotImplementedError()

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
    # --------------------------------
    def copy(self):
        """Create a new node representing a copy of the node's state.

        This method should start by creating a new "blank" node using ``clone = type(self)()``,
        which takes care of initializing generic MCTS node attributes, and then fill in the
        domain-specific data by shallow- or deep-copying the custom attributes that were
        previously defined in :meth:`root`. Note that some attributes should be unique for each
        node (hence copied deeply), while others can (and should, if possible) be shared among
        all nodes. This should be analyzed on a case-by-case basis.

        Returns:
            TreeNode: a clone of the current node.
        """
        raise NotImplementedError()

    def branches(self):
        """Generate a collection of branch objects that are available from the current node.

        This method should produce a collection (*e.g* list, tuple, set, generator) of branch
        objects. A branch object is an object (of any type, and with any internal structure)
        which carries enough information to apply a modification (through :meth:`apply`) to a
        copy of the current node and obtain one of its child nodes. In some cases, a branch
        object may be something as simple as a boolean value (see *e.g.* the knapsack example).

        Returns:
            collection of branch objects.
        """
        raise NotImplementedError()

    def apply(self, branch):
        """Mutate the node's state by applying a branch (as produced by :meth:`branches`).

        The logic in this method is highly dependent on the internal structure of the nodes and
        branch objects that are returned by :meth:`branches`.

        Note:
            This method should operate in-place on the node. The :meth:`expand` method will take
            care of creating copies of the current node and calling :meth:`apply` on the copies,
            passing each branch object returned by :meth:`branches` and thereby generating the
            list of the current node's children.

        Parameters:
            branch: an object which should contain enough information to apply a local
                modification to (a copy of) the current node, such that the end result represents
                descending one level in the tree.
        """
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
            z_node = self.sim_best.value
            z_best, z_worst = sols.feas_best.value, sols.feas_worst.value
            exploit_min, exploit_max = 0.5, 1.0  # TODO: remove hard-coded magic numbers
        else:
            z_node = self.sim_best.value.infeas
            z_best, z_worst = sols.infeas_best.value.infeas, sols.infeas_worst.value.infeas
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
        """Run a simulation from the current node to completion or infeasibility.

        This method defines the simulation strategy that is used to obtain node value estimates
        in MCTS. It should quickly descend the tree until a leaf node (solution or infeasibility)
        is reached, and return the result encountered.

        Smarter simulation strategies incorporate more domain-specific knowledge and normally use
        more computational resources, but can dramatically improve the performance of the
        algorithm. However, if the computational cost is too high, MCTS may be unable to gather
        enough data to improve the accuracy of its node value estimates, and will therefore end
        up wasting time in uninteresting regions. For best results, a balance between these
        conflicting goals must be reached.

        Returns:
            Solution: object containing the objective function value (or an :class:`Infeasible`
            value) and *optional* solution data.
        """
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
            if ancestor.sim_best.value > sol.value:
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
                    ancestor.sim_best = min(candidates, key=lambda s: s.value)
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

    def bound(self):
        """Compute a lower bound on the current subtree's optimal objective value.

        A :meth:`bound` method shoud be defined in subclasses intending to use pruning. By
        default, pruning will be automatically activated if the root node defines a :meth:`bound`
        method different from the one defined in the base :class:`TreeNode` class.

        Returns:
            a lower bound on the optimal objective function value in the subtree under the
            current node.
        """
        raise NotImplementedError()


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
