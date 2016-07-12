Introduction
============

Monte Carlo tree search is a very suitable algorithm for difficult problems where no good heuristics exist to evaluate a given partial solution or to decide which actions lead to better results. The algorithm builds a tree asymmetrically, using relatively simple rules to decide what nodes to explore next.

The basis of MCTS At its core, MCTS uses simulations to estimate the value of each node in the tree. These simulations normally include some degree of randomness, thereby being Monte Carlo simulations, which is found to lead to more robust estimates and better overall performance. The longer the algorithm runs, the larger the part of the search space that is covered, improving the quality of the node value estimates and in turn leading to better allocation of computational resources.
