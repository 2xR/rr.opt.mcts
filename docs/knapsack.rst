Knapsack example
================

This section explains the example implementation of MCTS for the `knapsack problem <https://en.wikipedia.org/wiki/Knapsack_problem>`_. This example can be found within the git repository at ``src/examples/knapsack.py``. The file begins with some auxiliary function definitions which are used to run some basic tests. We will skip those here and take a deeper look at the :class:`KnapsackTreeNode` implementation, which defines one possible structure and operations on tree nodes for this particular problem.

:meth:`root`
------------

We begin with the :meth:`KnapsackTreeNode.root` class method, where the internal structure of tree nodes is defined:

.. literalinclude:: ../src/examples/knapsack.py
    :lines: 73-84

Each tree node will have several domain-specific attributes:

``items_left``
    A list of :class:`Item` objects ordered by value-to-weight ratio. Items will be considered for packing in decreasing order of value-to-weight ratio.

``items_packed``
    List of items that have been added to the knapsack. Naturally, at the root node this is initialized as an empty list.

``capacity_required``
    The total weight of items that are still available to pack. We detect that a leaf node was reached when ``capacity_left`` is greater than or equal to ``capacity_required``.

``capacity_left``
    The unused capacity in the knapsack. Since at the root we have an empty solution with no items packed, this is initialized as the total knapsack capacity. Whenever an item is packed, this value will be reduced by the item's weight.

``total_value``
    This is the sum of the values of all packed items. Similar to ``capacity_left``, when packing a new item, ``total_value`` will be increased by the item's value.

``upper_bound``
    This is a cached result of the best possible value that is obtainable in the node's subtree. This is computed in the :meth:`bound` method on its first call, and subsequent calls will return the value stored in ``upper_bound``.

:meth:`copy`
------------

The next method we look at is :meth:`copy`. This method should simply create a copy of a given node:

.. literalinclude:: ../src/examples/knapsack.py
    :pyobject: KnapsackTreeNode.copy

The only noteworthy aspect in this method is that the attributes ``items_left`` and ``items_packed`` are copied using ``list()`` in order to create new lists with the same elements for the child node. Otherwise, both the parent and child nodes would refer to the same lists, which would lead to incorrect results. More generally, all data that should be local to each node must be deep-copied in some way, *i.e.* a simple assignment like ``clone.x = self.x`` does not suffice. In this particular example, the :class:`Item` objects themselves are not copied because they are immutable data which can (and should) be shared by all nodes.

:meth:`branches`
----------------

The next method is :meth:`branches`, defining our options to generate the children of a given node. The structure of the tree is defined by this method. In this example, it defines a binary tree, where each internal node has exactly two children -- pack or ignore the next item -- and leaf nodes have no children.

.. literalinclude:: ../src/examples/knapsack.py
    :pyobject: KnapsackTreeNode.branches

:meth:`apply`
-------------

The :meth:`apply` method takes an element from the list of branches returned by the :meth:`branches` method, and modifies the current node in-place. For the knapsack example, a branch object is simply a boolean value indicating whether or not to pack the highest-value-to-weight-ratio available item.

.. literalinclude:: ../src/examples/knapsack.py
    :pyobject: KnapsackTreeNode.apply

The first half of this method should be fairly straightforward: the highest value-to-weight ratio item is removed from the list of available items and then, if that item is to be packed, the node's attributes are updated appropriately. In the second ``if`` statement, the node is recognized as a leaf if all remaining items can fit in the available space.

:meth:`simulate`
----------------

The simulation strategy is defined by this method. Here, the simulation performs a dive in the tree using a simple uniform random selection of the branch to follow at each step. Then, the objective value of the solution obtained is multiplied by -1 because the :mod:`rr.opt.mcts.simple` implementation deals with minimization problems only, and the knapsack problem is a maximization problem.

.. literalinclude:: ../src/examples/knapsack.py
    :pyobject: KnapsackTreeNode.simulate

:meth:`bound`
-------------

Implementing a :meth:`bound` method allows the MCTS algorithm to use pruning as in traditional branch-and-bound algorithms. The value returned by this method *must* represent a lower bound on the best objective function value obtainable in the current subtree. If this best-case scenario value is not better than the best value found so far in the search, the entire subtree can be safely discarded, as it is guaranteed not to contain any improving solution. Depending on the "tightness" of this bound, this simple pruning idea can lead to a significant reduction of the size of the tree that must be explored, usually resulting in better performance.

In the knapsack example, we compute a simple yet tight bound that is equivalent to the linear relaxation of the mixed-integer programming formulation, *i.e.* we allow the last item packed in the knapsack to be partially packed in order to obtain maximum value from it. Like in the :meth:`simulate` method above, we must multiply the bound by -1.

.. literalinclude:: ../src/examples/knapsack.py
    :pyobject: KnapsackTreeNode.bound
