from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from future.builtins import object, dict, range

import sys
import math
import random

import gurobipy
from rr.opt import mcts


mcts.utils.config_logging(level="DEBUG")
logger = mcts.utils.logger
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


def set_var_bounds(domains):
    for vdata, (lb, ub) in domains.items():
        var = vdata.var
        var.lb = lb
        var.ub = ub


def solve_lp(model, domains):
    set_var_bounds(domains)
    model.optimize()
    return model.status == gurobipy.GRB.Status.OPTIMAL


class IntVarData(object):
    """A very basic wrapper around gurobi Var objects. This is necessary because gurobi Vars
    redefine comparison operators to simplify creation of expressions, e.g. x == y does not
    compare the two variables, but instead creates a LinExpr object. This is nice to create models
    in a more readable manner, but it breaks any lists or dicts of Var objects, as any attempt to
    remove them will remove the wrong Var object. Namely, it will remove the first var that it
    tries to compare to the target var, as it creates a LinExpr object (which when evaluated as a
    boolean returns True), therefore wrongly saying the any two Vars are equal."""

    def __init__(self, var):
        self.var = var
        self.name = var.VarName

    def __repr__(self):
        return "<IntVar {} @{:x}>".format(self.name, id(self))


class MipState(mcts.State):

    def __init__(self, filename):
        self.model = gurobipy.gurobi.read(filename)  # *shared* gurobi model :: Model
        self.model.params.outputFlag = 0

        self.domains = {}  # *local* variable domains :: {IntVarData: (lb, ub)}
        self.relaxed = []  # *local* free vars :: [IntVarData]
        self.upper_bound = None  # *local* upper bound :: float | Infeasible
        self.lower_bound = None  # *local* lower bound :: float | Infeasible

        # collect integer variables and relax them
        for var in self.model.getVars():
            if var.vType != gurobipy.GRB.CONTINUOUS:
                var.vType = gurobipy.GRB.CONTINUOUS
                lb = int(math.ceil(var.lb - EPS))
                ub = int(math.floor(var.ub + EPS))
                assert lb <= ub
                vdata = IntVarData(var)
                self.domains[vdata] = (lb, ub)
                self.relaxed.append(vdata)
        # ensure that list is ordered to maintain determinism
        self.relaxed.sort(key=lambda vd: vd.name)
        info("model has {} vars ({} int)".format(self.model.NumVars, self.model.NumIntVars))
        info("int vars: {}".format([vd.name for vd in self.relaxed]))
        assert len(self.domains) == len(self.relaxed) == self.model.NumIntVars

        self.propagate()  # reduce domains and fix any singleton variables
        self.solve_relaxation()  # solve root relaxation to determine bound
        info("ROOT RELAXATION:")
        for vdata in self.domains.keys():
            info("\t{}: {}".format(vdata.name, vdata.var.x))

    def fixed(self):
        return {vd.name: lb for vd, (lb, ub) in self.domains.items() if lb == ub}

    def __str__(self):
        return "\n".join([
            "NODE {:x} INFO:".format(id(self)),
            "\tfixed: {}".format(self.fixed()),
            "\trelaxed: {}".format([vd.name for vd in self.relaxed]),
            "\tupper_bound: {}".format(self.upper_bound),
            "\tlower_bound: {}".format(self.lower_bound),
        ])

    def copy(self):
        clone = mcts.State.copy(self)
        # global data (shallow-copied)
        clone.model = self.model
        # local data (which must be copied)
        clone.domains = dict(self.domains)
        clone.relaxed = list(self.relaxed)
        clone.upper_bound = self.upper_bound
        clone.lower_bound = self.lower_bound
        return clone

    def actions(self):
        if len(self.relaxed) == 0:
            return []
        vdata = random.choice(self.relaxed)
        lb, ub = self.domains[vdata]
        actions = [(vdata, value) for value in range(lb, ub+1)]
        random.shuffle(actions)
        return actions

    def apply(self, action):
        vdata, value = action
        lb, ub = self.domains[vdata]
        assert lb < ub
        assert lb <= value <= ub
        self.domains[vdata] = (value, value)
        self.relaxed.remove(vdata)
        self.solve_relaxation()
        if self.propagate():
            self.solve_relaxation()
        else:
            assert len(self.relaxed) == 0

    def solve_relaxation(self):
        # solve linear relaxation to find a lower bound for this state
        if solve_lp(self.model, self.domains):
            self.lower_bound = self.model.objVal
            # if all unfixed variables have integral values, we have a full solution
            if all(is_integral(vd.var.x) for vd in self.relaxed):
                for vdata in self.relaxed:
                    self.domains[vdata] = (vdata.var.x, vdata.var.x)
                self.relaxed = []
                self.upper_bound = self.model.objVal
        # otherwise we set an Infeasible as upper bound and make the node a leaf
        else:
            self.lower_bound = mcts.Infeasible(len(self.relaxed))
            self.upper_bound = mcts.Infeasible(len(self.relaxed))
            self.relaxed = []

    def simulate(self):
        # return a solution immediately if this is a leaf node
        if len(self.relaxed) == 0:
            return mcts.Solution(value=self.upper_bound, data=self.fixed())
        state = self.copy()
        state.solve_relaxation()  # determine variable values in initial LP
        while len(state.relaxed) > 0:
            vdata = random.choice(state.relaxed)
            value = vdata.var.x
            if random.random() < value - math.floor(value):
                value = int(math.ceil(value))
            else:
                value = int(math.floor(value))
            state.apply((vdata, value))
        return mcts.Solution(value=state.upper_bound, data=state.fixed())

    def bound(self):
        return self.lower_bound

    def propagate(self):
        set_var_bounds(self.domains)
        model = self.model
        obj_func = model.getObjective()
        obj_sense = model.ModelSense
        feasible = True

        while True:
            fixed = []
            for vdata in self.relaxed:
                var = vdata.var
                model.setObjective(var, gurobipy.GRB.MAXIMIZE)
                model.optimize()
                if model.status != gurobipy.GRB.Status.OPTIMAL:
                    feasible = False
                    break
                ub = int(math.floor(var.X + EPS))
                model.setObjective(var, gurobipy.GRB.MINIMIZE)
                model.optimize()
                assert model.status == gurobipy.GRB.Status.OPTIMAL
                lb = int(math.ceil(var.X - EPS))
                if lb > ub:
                    feasible = False
                    break

                prev_lb, prev_ub = self.domains[vdata]
                assert prev_lb <= lb
                assert prev_ub >= ub
                self.domains[vdata] = (lb, ub)
                var.lb = lb
                var.ub = ub
                if lb == ub:
                    fixed.append(vdata)

            if not feasible or len(fixed) == 0:
                break
            self.relaxed = [vd for vd in self.relaxed if vd not in fixed]

        if not feasible:
            self.upper_bound = mcts.Infeasible(len(self.relaxed))
            self.lower_bound = mcts.Infeasible(len(self.relaxed))
            self.relaxed = []
        model.setObjective(obj_func, obj_sense)
        return feasible


def main(instance, niter, seed):
    root = MipState(instance)
    solver = mcts.Solver(root, rng_seed=seed)
    best = solver.run(iter_limit=niter)
    info("best solution found: {}".format(best))
    if best.is_feas:
        info("best solution (non-zeros):")
        for var, val in best.data.items():
            if is_nonzero(val):
                info("\t{}:\t{}".format(var, val))
    return solver


usage = """usage: {prog} filename N seed
    where"
      - filename is in a format recognized by SCIP (mps, lp, ...)
      - N is the number of iterations
      - seed initializes the pseudo-random generator""".format(prog=sys.argv[0])


if __name__ == "__main__":
    if len(sys.argv) == 4:
        instance = sys.argv[1]
        niter = int(sys.argv[2])
        seed = int(sys.argv[3])
        main(instance, niter, seed)
    else:
        print(usage)
        exit(1)
