from .infeasible import Infeasible


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
