Introduction
============

Monte Carlo tree search (MCTS) is a very suitable algorithm to tackle difficult problems for which there are no known good (value or policy) heuristics. The algorithm builds a search tree asymmetrically, using relatively simple rules to decide what nodes to explore next.

The core concept of MCTS is that of Monte Carlo simulations, which are used to estimate the value of tree nodes. The term "Monte Carlo" is used here to indicate that some degree of probabilistic behavior is included in the simulation, and that repetition is used to improve the accuracy of the method, as in the traditional meaning of Monte Carlo methods. In an extreme case, actions are randomly selected with uniform probability at each step of the simulation until a leaf is reached -- in the context of optimization, this is either a feasible or infeasible solution.

As more time is alotted to the algorithm, a larger part of the search space is covered and the quality of the node value estimates is improved, especially for nodes closer to the root. This focuses the search on the most promising regions of the tree, and in turn leads to better allocation of computational resources. However, the node selection strategy typically incorporates a term to promote exploration of unknown regions. This term is combined with an exploitation-oriented term, which tends to narrow the scope of the search to the areas around known good solutions.

Below is a highly simplified pseudo-code version of the algorithm for maximization problems:

.. code-block:: python

    def mcts(root):
        # initialization
        best = simulation(root)
        backprogation(best, start_at=root)
        # main loop
        while time_remaining() and not exhausted(root):
            node = selection(start_at=root)
            for child in expansion(node):
                leaf = simulation(start_at=child)
                if value(leaf) > value(best):
                    best = leaf
                backpropagation(leaf, start_at=child)
        return best

The code shows the four main components of MCTS -- selection, expansion, simulation, and backpropagation -- which are described in greater detail in the following sections.


Selection
---------

The role of the selection policy is to traverse the tree and pick the node which seems most promising to be expanded in the current iteration. As the notion of "promising" varies according to the current node value estimates and search history, the tree normally grows in an asymmetric manner.

Selection starts with the root as the current node and, at each level, picks the best child of the current node with respect to some measure of node potential. As mentioned above, this is typically achieved through a combination of exploration- and exploitation-oriented terms.


Expansion
---------

Node expansion determines the structure of the tree, *i.e.* how child nodes are obtained from the selected node. The same problem can be seen from multiple perspectives and lead to different tree structures, *e.g.* binary *vs* n-ary trees. This decision can have a great impact on the algorithm's performance, though this is practically impossible to ascertain.


Simulation
----------

The objective of the simulation step is to make a quick dive and attempt to find complete (feasible) solutions. Even if that cannot be achieved, the degree of infeasibility of a solution found during a simulation can be used to guide subsequent iterations of the algorithm.

Ideally, simulations should be computationally cheap in order to afford as many simulations as possible within the alloted computational budget. Expensive simulations would not allow much information to be gathered and value estimates to improve.


Backpropagation
---------------

Each node in the tree keeps a list of simple statistics and data that are used to compute the node's value estimate for the selection step. These data can include the number of simulations run under that node's subtree, the best solution found therein, and possibly other information. The backpropagation step consists in updating these statistics for all nodes between the root and the child which originated the simulation. This means that all nodes in the selection path will have their value estimates updated, hopefully increasing their accuracy.
