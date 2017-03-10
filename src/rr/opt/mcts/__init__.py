from .infeasible import Infeasible
from .solution import Solution
from .solver import Solver
from .state import State
from .tree import TreeNode
from . import utils
try:
    from . import viz
except ImportError:
    viz = None


__version__ = "0.4.0"
__author__ = "Rui Rei"
__copyright__ = "Copyright 2016-2017 {author}".format(author=__author__)
__license__ = "MIT"
