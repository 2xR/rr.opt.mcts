from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import random

from .utils import blank_instance


class State(object):
    """Base class for tree states. These objects possess no reserved attributes and have a minimal
    public interface that they must define.

    The only mandatory methods are `copy()`, `actions()`, and `apply()`, plus at least one of
    `simulate()` or `solution()`. However, it is recommended to also implement the remaining
    methods whenever possible.

    There are some dependencies between `is_terminal()`, `simulate()`, and `solution()`. Please
    refer to these methods' docstrings for details.
    """

    def copy(self):
        """Base copy() operation, used by subclasses to obtain a blank instance.

        Subclass implementations of :meth:`copy` should call this method to obtain a blank
        instance and then populate the object explicitly.

        Note:
            This does not call :meth:`__init__` on the newly created object. Any object
            initialization should be done explicitly within the subclass' implementation of
            :meth:`copy`.
        """
        return blank_instance(type(self))

    def actions(self):
        """Produce an iterable containing the actions available from this state."""
        raise NotImplementedError()

    def apply(self, action):
        """Apply the argument action to this state, modifying it in-place."""
        raise NotImplementedError()

    def is_terminal(self):
        """Boolean indicating whether this is a terminal state (*i.e.* a leaf) or not.

        This is an optional method, but if provided, allows nodes containing terminal states to
        be removed from the tree after simulation and backpropagation occurs **in the same MCTS
        iteration** where they were created. If the method is not provided, then these nodes
        remain in the tree until they're selected at a later iteration, which will only serve to
        learn that the node has no children and can be removed from the tree.

        Warning:
            If this method is redefined, then the `solution()` method must also be implemented.
        """
        return False

    def bound(self):
        """Provide a lower bound on the objective function values obtainable from this state.

        This method is optional. If it is provided, pruning will be enabled be default. You can
        still manually disable it through the solver's `pruning` attribute.
        """
        raise NotImplementedError()

    def simulate(self):
        """Run one or more simulations to terminal states, and return the solution(s) produced.

        Note:
            Optional method. If this method is not redefined, then `solution()` is required.

        This method defines the simulation strategy that is used to obtain node value estimates
        in MCTS. It should quickly dive down the tree until a terminal state is reached,
        and return the result encountered.

        Smarter simulation strategies incorporate more domain-specific knowledge and normally use
        more computational resources, but can dramatically improve the performance of the
        algorithm. However, if the computational cost is too high, MCTS may be unable to gather
        enough data to improve the accuracy of its node value estimates, and will therefore end
        up wasting time in uninteresting regions. For best results, a balance between these
        conflicting goals must be reached.

        The default implementation does a single uniform random simulation and returns the
        solution obtained from the resulting terminal state. If you choose *not to* implement a
        custom simulation strategy (*i.e.* go with the default), then the `solution()` method
        must be defined. The default behavior can be used as a first approach, or when there are
        no known good heuristics for a particular problem.

        Returns:
            A :class:`Solution` object or an iterable of :class:`Solution` objects. Each solution
            returned contains an objective function value (or an :class:`Infeasible` value) and
            *optional* solution data.
        """
        state = self.copy()
        while not state.is_terminal():
            actions = list(state.actions())
            if len(actions) == 0:
                break
            state.apply(random.choice(actions))
        return state.solution()

    def solution(self):
        """Produce a `Solution` object corresponding to this (terminal) state.

        Note:
            Optional method, required only if either:
            - `is_terminal()` *is* redefined, or
            - `simulate()` *is not* redefined.
        """
        raise NotImplementedError()
