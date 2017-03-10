from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import collections
import random

from .expansion import Expansion
from .infeasible import Infeasible
from .solution import Solution, SolutionTracker
from .stats import Stats
from .utils import UNDEFINED, max_elems


class NaryTreeNode(object):
    """A simple base class defining n-ary tree nodes, *i.e.* each node can have exactly one
    parent node and an arbitrary number of child nodes.

    This code is separate from the MCTS TreeNode class in order to keep things clean. This class
    *knows nothing* about MCTS.
    """

    def __init__(self):
        self.children = []  # list of child nodes
        self.ancestors = ()  # tuple of ancestor nodes (bottom-up, starting from parent)
        self.parent = None  # reference to the parent node
        self.root = self  # reference to the root of the tree this node is attached to
        self.depth = 0  # this node's depth in the tree, i.e. its number of ancestors

    def add_child(self, node):
        if len(node.ancestors) > 0 or len(node.children) > 0:
            raise ValueError("argument node cannot have ancestors or children")
        self.children.append(node)
        node.ancestors = (self,) + self.ancestors
        node.parent = self
        node.root = self.root
        node.depth = self.depth + 1

    def remove_child(self, node):
        if node.parent is not self:
            raise ValueError("argument node has a different parent")
        self.children.remove(node)
        node.ancestors = ()
        node.parent = None
        node.root = node
        node.depth = 0

    def iter_preorder(self):
        """Depth-first iterator that visits nodes *before* their children."""
        stack = [self]
        while len(stack) > 0:
            node = stack.pop()
            yield node
            if len(node.children) > 0:
                stack.extend(node.children)

    def iter_postorder(self):
        """Depth-first iterator that visits nodes *after* their children."""
        stack = [(self, False)]
        while len(stack) > 0:
            node, children_visited = stack.pop()
            if children_visited or len(node.children) == 0:
                yield node
            else:
                stack.append((node, True))
                stack.extend((child, False) for child in node.children)

    __iter__ = iter_preorder

    def tree_size(self):
        """The number of nodes in this (sub-)tree."""
        return sum(1 for _ in self.iter_preorder())

    def tree_height(self):
        """The number of levels in this (sub-)tree."""
        return 1 + max(n.depth for n in self.iter_preorder())


class TreeNode(NaryTreeNode):
    """Base class for MCTS tree nodes. Builds upon :class:`NaryTreeNode` by including attributes
    and methods related to Monte Carlo tree search.

    Users can customize the behavior of MCTS by subclassing this class. In most applications,
    however, the only requirement is a subclass of :class:`State` implementing the problem
    specific details.
    """

    Stats = Stats
    Expansion = Expansion

    def __init__(self, state, action=UNDEFINED):
        NaryTreeNode.__init__(self)
        cls = type(self)
        self.state = state  # reference to a problem-dependent state associated with this node
        self.action = action  # reference to the action that led to this state
        self.stats = cls.Stats(self)  # node statistics accumulator
        self.expansion = cls.Expansion(state)  # lazy state expansion manager
        self.cached_bound = None  # attr used to cache the node's objective bound

    @property
    def is_exhausted(self):
        """True iff the node is fully expanded and all its children were removed from the tree.

        Exhausted nodes can/should be removed from the tree.
        """
        return self.expansion.is_finished and len(self.children) == 0

    # This parameter controls interleaved selection of still-expanding parent nodes with their
    # children, thereby allowing the search to deepen without forcing the full expansion of all
    # ancestors. Turn off to force parents to be fully expanded before starting to select their
    # children.
    SELECTION_INTERLEAVING = False

    def select(self):
        """Go down the tree picking the "best" (*i.e.* with highest selection_score()) child at
        each step.
        """
        node = self
        selection_score = type(self).selection_score
        allow_interleaving = self.SELECTION_INTERLEAVING
        while True:
            expansion = node.expansion
            if not expansion.is_started or not expansion.is_finished and not allow_interleaving:
                break
            cands, max_score = max_elems(node.children, key=selection_score)
            if not expansion.is_finished and allow_interleaving:
                node_score = selection_score(node)
                if node_score > max_score:
                    cands = [node]
                elif node_score == max_score:
                    cands.append(node)
            next_node = cands[0] if len(cands) == 1 else random.choice(cands)
            if next_node is node:
                break
            node = next_node
        return node

    def selection_score(self):
        stats = self.stats
        return stats.opt_exploitation_score() + stats.uct_exploration_score()

    # Parameter controlling how many child nodes (at most) are created for each call to expand()
    # (normally one per iteration of MCTS). The default value is 1, which means that nodes are
    # expanded one child at a time. This allows the algorithm to pick other sites for exploration
    #  if the initial children of the current node reveal it to be a bad choice.
    EXPANSION_LIMIT = 1

    def expand(self, pruning=False):
        """Create and link (after performing optional pruning checks) new child nodes.

        This uses the node's expansion object to obtain new (action, state) pairs and creates
        child nodes from those. For each new node, we check the bound (if `pruning` is enabled)
        and only if that check passes do we link the node to the tree.

        At the end of the expansion loop, if the parent node is exhausted (*i.e.* fully expanded
        and childless) it is removed from the tree.
        """
        expansion = self.expansion
        if not expansion.is_started:
            assert len(self.children) == 0
            expansion.start()
        cls = type(self)
        count = 0
        limit = cls.EXPANSION_LIMIT
        root_stats_overall = self.root.stats.overall
        while count < limit and not expansion.is_finished:
            action, state = expansion.next()
            child = cls(state, action)
            cutoff = root_stats_overall.best.value
            if not pruning or isinstance(cutoff, Infeasible) or child.bound() < cutoff:
                self.add_child(child)
                yield child
            count += 1
        if expansion.is_finished:
            if len(self.children) == 0:
                self.delete()
            else:
                self.expansion_finished()

    def expansion_finished(self):
        """Called when the node's expansion is complete, but the node is not yet exhausted. This
        can be used to save resources *e.g.* by releasing the memory taken by the node's state.
        """
        self.bound()  # ensures we cache the node's bound before getting rid of the state
        self.state = None

    def simulate(self):
        """Produce one or more solutions through randomized simulations from this node's state.

        The `state.simulate()` method can either return a single :class:`Solution` object,
        or an iterable of :class:`Solution` objects, but the Solver is expecting an iterable of
        Solution objects. Therefore, this method converts the result of `state.simulate()`,
        if necessary, into an iterable of :class:`Solution` objects.
        """
        result = self.state.simulate()
        if isinstance(result, Solution):
            return [result]
        if isinstance(result, collections.Iterable):
            return result
        raise TypeError("unexpected result from node.simulate() => {}".format(result))

    def backpropagate(self, sol):
        """Integrate a simulation solution into the statistics of this node and its ancestors."""
        self.stats.update(sol, self)
        for ancestor in self.ancestors:
            ancestor.stats.update(sol, self)

    def bound(self):
        """Compute a lower bound on the current subtree's optimal objective value.

        This method calls `bound()` on the underlying state and caches the value, so that later
        calls to this method will not recompute the bound.

        Returns:
            a lower bound on the optimal objective function value in the current subtree.
        """
        bound = self.cached_bound
        if bound is None:
            bound = self.cached_bound = self.state.bound()
        return bound

    def prune(self, cutoff):
        """Discard nodes/subtrees which can no longer lead to a solution better than `cutoff`."""
        assert not isinstance(cutoff, Infeasible)
        stack = [self]
        while len(stack) > 0:
            node = stack.pop()
            if node.bound() >= cutoff:
                node.delete()
            else:
                stack.extend(node.children)

    def delete(self):
        """Remove a node from the search tree and refresh its ancestors' statistics.

        The actual node to be removed may not be the node on which `delete()` was called,
        but one of its ancestors. The first phase of this method goes up the tree while the
        parent of the current node is fully expanded and has exactly one child. Note that this
        would make the parent "exhausted" after removing the current node, so we move up one
        level and check again. Once the appropriate point of detachment is found, the node is
        removed from the tree and the stats of its ancestors are recomputed, taking into account
        that some solutions are no longer available due to the node/subtree being removed.
        """
        # Go up the tree while the current node has a parent that is fully expanded and has only
        # one child left (which is the current node!). This traversal up the tree stops when the
        # root is reached (obviously) or the parent is either not yet fully expanded or has
        # children other than the current node.
        node = self
        parent = self.parent
        while parent is not None and parent.expansion.is_finished and len(parent.children) == 1:
            assert parent.children[0] is node
            node = parent
            parent = node.parent
        # Now we have three cases:
        # a) we've reached the root, and
        #    1) root has a single child, in which case we must detach the child.
        #    2) root has no children, which means that .delete() was called directly on the root.
        #       This could be because of pruning or the expansion of the root has finished and
        #       all its children have already been removed. Very unlikely but still valid cases.
        #    The root's stats must be refreshed and should become empty if everything is correct.
        # b) we stopped short of the root, and we must remove the current node from the tree, and
        #    then refresh the stats of its ancestors. It is important that ancestor stats are
        #    refreshed in bottom-up order. Also, we can stop refreshing as soon as we see one
        #    refresh that doesn't cause any changes in stats.
        if parent is None:
            assert node is self.root and len(node.children) < 2
            if len(node.children) > 0:
                node.remove_child(node.children[0])
            node.stats.refresh()
            assert (
                node.stats.feas.best is SolutionTracker.INIT_BEST and
                node.stats.feas.worst is SolutionTracker.INIT_WORST and
                node.stats.infeas.best is SolutionTracker.INIT_BEST and
                node.stats.infeas.worst is SolutionTracker.INIT_WORST and
                node.stats.overall.best is SolutionTracker.INIT_BEST and
                node.stats.overall.worst is SolutionTracker.INIT_WORST
            )
        else:
            ancestors = node.ancestors  # grab a reference before remove_child() is called
            parent.remove_child(node)
            assert not parent.is_exhausted
            for ancestor in ancestors:
                if not ancestor.stats.refresh():
                    break
