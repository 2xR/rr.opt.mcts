Using ``rr.opt.mcts.basic``
===========================

The ``rr.opt.mcts.basic`` module provides a simple, self-contained [#]_ implementation of Monte Carlo tree search, and a framework for users to define their own ``TreeNode`` classes for specific problems.

To use the framework, a user should simply define their own tree node class by subclassing ``TreeNode``. The ``TreeNode`` base class defines some internal attributes that are used to manage parent-child connections and keep track of simulations. Node objects can define their own internal structure freely, with the exception of the names ``path``, ``parent``, ``children``, ``sim_count``, ``sim_sol`` and ``sim_best``, as these are used for the aforementioned purposes.


and also some abstract methods which are needed for the operation of MCTS, *e.g.* how to perform a simulation. These abstract methods must be

 These attributes are used internally


Abstract methods:


.. py:module:: rr.opt.mcts.basic

.. autoclass:: TreeNode
	:members:



Limitations
-----------

#. minimization only



.. [#] The module depends only on the ``future`` library for cross-version compatibility with Python 2 and 3.
