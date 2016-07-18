Using ``rr.opt.mcts.basic``
===========================

The ``rr.opt.mcts.basic`` module provides a simple, self-contained [#]_ implementation of Monte Carlo tree search, and a framework for users to define their own ``TreeNode`` classes for specific problems.

To use the framework, a user should simply define their own tree node class by subclassing :class:`TreeNode`. The :class:`TreeNode` base class defines some internal attributes that are used to manage parent-child connections and keep track of simulations. Node objects can define their own internal structure freely, with the exception of the names ``path``, ``parent``, ``children``, ``sim_count``, ``sim_sol`` and ``sim_best``, as these are used for the aforementioned purposes.

While the base ``TreeNode`` class takes care of generic MCTS-related operations, problem-specific logic must be implemented in subclasses by defining a few methods. These methods are documented below.

.. py:module:: rr.opt.mcts.basic

.. py:class:: TreeNode

    .. automethod:: root

    .. automethod:: copy

    .. automethod:: branches

    .. automethod:: apply

    .. automethod:: simulate

    .. automethod:: bound


Defining problem-specific node attributes
-----------------------------------------

Problem-specific node attributes should not be added in the regular Python object initializer method ``__init__()``. In fact, the ``__init__()`` method should preferably not be redefined by subclasses. Instead, these additional instance attributes should be defined in the :meth:`TreeNode.root` class method, and replicated in :meth:`TreeNode.copy`.

.. code-block:: python

    class FooNode(TreeNode):
        @classmethod
        def root(cls, instance):
            root = cls()
            root.instance = instance
            root.bar = 42
            root.ham = ["spam"]
            return root

        def copy(self):
            clone = type(self)()
            clone.instance = self.instance
            clone.bar = self.bar
            clone.ham = list(self.spam)
            return clone


Running the algorithm
---------------------

Once a custom :class:`TreeNode` class has been defined, MCTS can be run as in the following example:

.. code-block:: python

    from pprint import pprint as print
    from rr.opt.mcts import basic as mcts
    from myproblem import MyTreeNode

    sols = mcts.run(root=MyTreeNode.root(instance), iter_limit=1e10, time_limit=3600)
    print(sols.best.obj)  # objective function value of the best solution found
    print(sols.best.data)  # solution data
    print(sols.best.is_opt)  # boolean indicating whether the best solution found is optimal


Limitations
-----------

#. the implementation can only deal with minimization problems. This is simple to work around however: simply multiply all objective function and bound values by -1.
#. all child nodes are created in one iteration. This may lead to a large waste of computational resources running simulations on uninteresting nodes.
#. Does not yet stop early if the bound and incumbent are equal (should add this).

.. rubric:: Footnotes

.. [#] The module depends only on the ``future`` library for cross-version compatibility with Python 2 and 3.
