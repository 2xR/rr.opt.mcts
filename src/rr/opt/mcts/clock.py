from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import contextlib
import time


class Clock(object):
    """Clock object for CPU tracking. To track the CPU time of a function just call it in a
    `tracking()` context block:

    .. code-block:: python

        clock = Clock()
        with clock.tracking():
            do_stuff()
        print("Elapsed CPU time:", clock.elapsed)
    """

    def __init__(self):
        self._start = None
        self._elapsed = 0.0
        self._tracks = 0  # count number of active tracks to handle reentrance correctly

    def __repr__(self):
        return "<{}({} sec) @{:x}>".format(type(self).__name__, self.elapsed, id(self))

    @property
    def is_active(self):
        """True iff the clock is tracking time (*i.e.* has been `start()`ed)."""
        return self._tracks > 0

    @property
    def elapsed(self):
        """Get the current elapsed cpu time.

        This property will maintain the same value while the clock is inactive, but will always
        have different (increasing) values while the clock is active. This works correctly inside
        `tracking()` contexts, and handles nesting/reentrance correctly.
        """
        if self._tracks > 0:
            return self._elapsed + (time.clock() - self._start)
        else:
            return self._elapsed

    def reset(self, force=False):
        """Set the clock back to zero. `force` is required if the clock is active."""
        if not force and self._tracks > 0:
            raise Exception("cannot reset; clock is currently active (use 'force=True'?)")
        self._start = None
        self._elapsed = 0.0
        self._tracks = 0

    clear = reset  # provide a common alias for `reset`

    def start(self):
        if self._tracks == 0:
            self._start = time.clock()
        self._tracks += 1

    def stop(self):
        if self._tracks > 0:
            self._tracks -= 1
            if self._tracks == 0:
                self._elapsed += time.clock() - self._start
                self._start = None

    @contextlib.contextmanager
    def tracking(self):
        self.start()
        try:
            yield self
        finally:
            self.stop()
