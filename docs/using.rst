Using :mod:`rr.opt.mcts.simple`
===============================

The :mod:`rr.opt.mcts.simple` module provides a simple, self-contained\ [#]_ implementation of Monte Carlo tree search, and a framework for users to define their own :class:`TreeNode` classes for specific problems.

To use the framework, a user should simply define their own tree node class by subclassing :class:`TreeNode`. The :class:`TreeNode` base class defines some internal attributes that are used to manage parent-child connections and keep track of simulations. Node objects can define their own internal structure freely, with the exception of the names ``path``, ``parent``, ``children``, ``sim_count``, ``sim_sol`` and ``sim_best``, as these are used for the aforementioned purposes. While the base :class:`TreeNode` class takes care of general MCTS-related operations, problem-specific logic must be implemented in subclasses by defining a few methods. These methods are documented below.

.. py:module:: rr.opt.mcts.simple

.. autoclass:: TreeNode

    .. automethod:: root

    .. automethod:: copy

    .. automethod:: branches

    .. automethod:: apply

    .. automethod:: simulate

    .. automethod:: bound

.. autoclass:: Solution

.. autoclass:: Infeasible


Defining custom node attributes
-------------------------------

Problem-specific node attributes should not be added in the regular Python object initializer method ``__init__()``. In fact, the ``__init__()`` method should preferably not be redefined by subclasses, as nodes are automatically created by the MCTS framework through the :meth:`TreeNode.copy` method. The recommended way to define additional instance attributes is to add them in the :meth:`TreeNode.root` class method, and replicate the node's custom structure appropriately in :meth:`TreeNode.copy`.

.. code-block:: python

    class FooNode(mcts.TreeNode):
        @classmethod
        def root(cls, instance):
            root = cls()
            root.instance = instance
            root.shared_state = ExampleSharedState()
            root.bar = 42
            root.ham = ["spam"]
            return root

        def copy(self):
            clone = mcts.TreeNode.copy(self)
            clone.instance = self.instance
            clone.shared_state = self.shared_state
            clone.bar = self.bar
            clone.ham = list(self.spam)
            return clone


Writing a :meth:`simulate` method
---------------------------------

The simulation algorithm lies at the heart of MCTS, and its goal is to reach a full solution or infeasibility by quickly diving down the search tree in a possibly (semi-)randomized manner. In the :mod:`rr.opt.mcts.simple` framework, the simulation algorithm should be defined as a :meth:`simulate` method within your :class:`TreeNode` subclass. The only requisite on the :meth:`simulate` method is that it must return a :class:`Solution` object.

:class:`Solution` objects contain a value representing the solution's objective function value for feasible solutions, or its degree of infeasibility (see :class:`Infeasible`) otherwise. Also, the constructor of the :class:`Solution` object can take a ``data`` argument, which is an object of any type that is meant to represent the actual solution, *i.e.* a complete set of decision variable assignments. This is helpful if something is to be done with the solutions found, after the algorithm has finished running. The :mod:`rr.opt.mcts.simple` framework does not use solution data for any purpose, therefore attaching solution data to a :class:`Solution` object is entirely optional. However, the solution value **must** be present.


Running the algorithm
---------------------

Once a custom :class:`TreeNode` class has been defined, MCTS can be run as in the following example:

.. code-block:: python

    from rr.opt.mcts import basic as mcts
    import myproblem

    instance = myproblem.load("./instance_01.json")
    root = myproblem.TreeNode.root(instance)
    sols = mcts.run(
        root=root,
        iter_limit=1e10,
        time_limit=3600,
        rng_seed=42,
    )
    print(sols.best.value)  # objective function value of the best solution found
    if sols.best.is_feas:  # check if we found a feasible solution
        print(sols.best.data)  # solution data
        print(sols.best.is_opt)  # boolean indicating whether the best solution found is optimal

The parameters and return value of the :func:`rr.opt.mcts.simple.run` function are documented below:

.. autofunction:: run



Caveat: solving maximization problems
-------------------------------------

It should be noted that this simple MCTS implementation can only deal with minimization problems. However, it is easy to work around this limitation and deal with maximization problems by multiplying all objective function and bound values by :math:`-1` (see, *e.g.* the :doc:`Knapsack example <./knapsack>`).


.. rubric:: Footnotes

.. [#] The module depends only on the ``future`` library for cross-version compatibility with Python 2 and 3.
