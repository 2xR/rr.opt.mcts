from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from future.builtins import object, dict, range

import math

import gurobipy
import rr.opt.mcts.basic as mcts


random = mcts.random
mcts.config_logging(level="DEBUG")
logger = mcts.logger
info = logger.info
debug = logger.debug

EPS = 1e-9


# utility functions
def is_approx(x, y):
    return abs(x - y) <= EPS


def is_integral(x):
    return abs(x - round(x)) <= EPS


def is_nonzero(x):
    return abs(x) > EPS


def verify_sol(filename, sol):
    print("checking", filename)
    model = gurobipy.gurobi.read(filename)
    model.params.outputFlag = 0

    intvars = []
    for v in model.getVars():
        if v.vType != gurobipy.GRB.CONTINUOUS:
            intvars.append(v)
            v.vType = gurobipy.GRB.CONTINUOUS

    assert {v.VarName for v in intvars} == set(sol.data.keys())
    for v in intvars:
        x = sol.data[v.VarName]
        v.lb = v.ub = x
        print("\t{}: {}".format(v.VarName, x))

    model.optimize()
    assert model.status == gurobipy.GRB.Status.OPTIMAL
    assert all(is_integral(v.x) for v in intvars)
    assert is_approx(model.objVal, sol.obj)
    print("solution passed all checks")


class MipTreeNode(mcts.TreeNode):
    class IntVarData(object):
        def __init__(self, var):
            self.var = var
            self.name = var.VarName
            self.lb = int(math.ceil(var.lb))
            self.ub = int(math.floor(var.ub))
            assert self.lb <= self.ub

        def __repr__(self):
            return "<IntVar {}[{},{}] @{:x}>".format(self.name, self.lb, self.ub, id(self))

    @classmethod
    def root(cls, filename):
        root = cls()
        root.model = gurobipy.gurobi.read(filename)
        root.model.params.outputFlag = 0

        # some global data
        # collect integer variables and relax them
        root.ivar_data = []  # list of var data for integer vars :: [vardata]
        for var in root.model.getVars():
            if var.vType != gurobipy.GRB.CONTINUOUS:
                var.vType = gurobipy.GRB.CONTINUOUS
                root.ivar_data.append(cls.IntVarData(var))
        root.ivar_data.sort(key=lambda vd: vd.name)
        info("model has {} vars ({} int)".format(len(root.model.getVars()), len(root.ivar_data)))
        info("int vars: {}".format([vd.name for vd in root.ivar_data]))

        # data to be kept in each node
        root.fixed = dict()  # values of fixed vars :: {vardata: val}
        root.relaxed = list(root.ivar_data)  # vars which are not fixed yet :: [vardata]
        root.upper_bound = None  # node upper bound :: float
        root.lower_bound = None  # node lower bound :: float

        # immediately get rid of any singleton variables
        for vdata in root.ivar_data:
            if len(root.relaxed) > 0 and vdata.lb == vdata.ub:
                root.apply(branch=(vdata, vdata.lb))
        root.solve_relaxation()  # solve root relaxation to determine bound
        return root

    def __str__(self):
        return "\n".join([
            "NODE {:x} INFO:".format(id(self)),
            "\tfixed: {}".format({vd.name: val for vd, val in self.fixed.items()}),
            "\trelaxed: {}".format([vd.name for vd in self.relaxed]),
            "\tupper_bound: {}".format(self.upper_bound),
            "\tlower_bound: {}".format(self.lower_bound),
            "\tsim_count: {}".format(self.sim_count),
            "\tsim_sol: {}".format(self.sim_sol),
            "\tsim_best: {}".format(self.sim_best),
        ])

    def copy(self):
        clone = type(self)()
        # global data (shallow-copied)
        clone.model = self.model
        clone.ivar_data = self.ivar_data
        # local data (which must be copied)
        clone.fixed = dict(self.fixed)
        clone.relaxed = list(self.relaxed)
        clone.upper_bound = self.upper_bound
        clone.lower_bound = self.lower_bound
        return clone

    def branches(self):
        if len(self.relaxed) == 0:
            return []
        vdata = random.choice(self.relaxed)
        return [(vdata, value) for value in range(vdata.lb, vdata.ub + 1)]

    def apply(self, branch):
        vdata, value = branch
        assert vdata not in self.fixed
        self.fixed[vdata] = value
        self.relaxed.remove(vdata)
        self.solve_relaxation()

    def solve_relaxation(self):
        # set up bounds of *all* integer variables
        for vdata in self.ivar_data:
            var = vdata.var
            val = self.fixed.get(vdata, None)
            if val is not None:
                var.lb = val
                var.ub = val
            else:
                var.lb = vdata.lb
                var.ub = vdata.ub
        # solve subproblem
        self.model.optimize()
        # if feasible, we have a lower bound for this node
        if self.model.status == gurobipy.GRB.Status.OPTIMAL:
            self.lower_bound = self.model.objVal
            # if all unfixed variables have integral values, we have a full solution
            if all(is_integral(vd.var.x) for vd in self.relaxed):
                for vdata in self.relaxed:
                    self.fixed[vdata] = vdata.var.x
                self.relaxed = []
                self.upper_bound = self.model.objVal
                assert len(self.fixed) == len(self.ivar_data)
        # otherwise we set an Infeasible as upper bound and make the node a leaf
        else:
            self.lower_bound = mcts.Infeasible(len(self.relaxed))
            self.upper_bound = mcts.Infeasible(len(self.relaxed))
            self.relaxed = []

    def simulate(self):
        # return a solution immediately if this is a leaf node
        if len(self.relaxed) == 0:
            return mcts.Solution(
                obj=self.upper_bound,
                data={vd.name: val for vd, val in self.fixed.items()},
            )
        node = self.copy()
        while len(node.relaxed) > 0:
            vdata = random.choice(node.relaxed)
            value = vdata.var.x
            if random.random() < value - math.floor(value):
                value = math.ceil(value)
            else:
                value = math.floor(value)
            node.apply((vdata, value))
        return mcts.Solution(
            obj=node.upper_bound,
            data={vd.name: val for vd, val in node.fixed.items()},
        )

    def bound(self):
        return self.lower_bound


def main(instance, niter, seed):
    root = MipTreeNode.root(instance)
    sols = mcts.run(root, iter_limit=niter, seed=seed)
    print("solutions found:", sols)
    print("best found objective:", sols.best.obj)
    if sols.best.is_feas:
        print("best solution (non-zeros):")
        for var, val in sols.best.data.items():
            if is_nonzero(val):
                print("\t{}:\t{}".format(var, val))
    return root, sols


if __name__ == "__main__":
    import sys

    if len(sys.argv) == 4:
        instance = sys.argv[1]
        niter = int(sys.argv[2])
        seed = int(sys.argv[3])
        main(instance, niter, seed)
    else:
        print("usage: {} filename N seed".format(sys.argv[0]))
        print("    where")
        print("      - filename is in a format recognized by SCIP (mps, lp, ...)")
        print("      - N is the number of iterations")
        print("      - seed initializes the pseudo-random generator")
        exit(1)
