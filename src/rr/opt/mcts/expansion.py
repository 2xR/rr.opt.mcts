from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from .utils import UNDEFINED


class Expansion(object):
    """Lazy generator of child states.

    This object creates a copy of a given parent state and applies the next unexpanded action on
    demand. Once the parent state has been completely expanded, *i.e.* all actions have been
    consumed, the `is_finished` flag will be set to true.

    Calling `next()` on an unstarted or finished expansion object will raise `ValueError`.
    """

    def __init__(self, state):
        self.state = state
        self.next_action = UNDEFINED
        self.remaining_actions = UNDEFINED
        self.is_started = False
        self.is_finished = False

    def start(self):
        if self.is_started:
            raise ValueError("multiple attempts to start node expansion")
        self.remaining_actions = iter(self.state.actions())
        self.is_started = True
        self._advance()

    def next(self):
        if not self.is_started:
            raise ValueError("node expansion is not yet started")
        if self.is_finished:
            raise ValueError("node expansion is already finished")
        action = self.next_action
        child = self.state.copy()
        child.apply(action)
        self._advance()
        return action, child

    def _advance(self):
        try:
            self.next_action = next(self.remaining_actions)
        except StopIteration:
            self.next_action = UNDEFINED
            self.remaining_actions = UNDEFINED
            self.is_finished = True
