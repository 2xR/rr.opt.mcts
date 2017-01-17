from .stats import TreeNodeStats


class TreeNode(object):
    State = None
    Stats = TreeNodeStats

    def __init__(self, state, prev_action=None):
        cls = type(self)
        self.path = ()  # path from root down to, but excluding, 'self' (i.e. top-down ancestors)
        self.parent = None  # reference to parent node
        self.children = None  # list of child nodes (when expanded)
        self.actions = None  # list of unexpanded actions
        self.prev_action = prev_action  # action that led to this state
        self.state = state  # the node's associated state
        self.stats = cls.Stats(self)  # node statistics

    @property
    def depth(self):
        """Depth of the node in the tree, *i.e.* the number of ancestors of the current node."""
        return len(self.path)

    @property
    def is_expanded(self):
        """True iff the node's expansion has finished."""
        return self.expansion.is_finished

    @property
    def is_exhausted(self):
        """True iff the node is fully expanded and all its children were removed from the tree."""
        return self.is_expanded and len(self.children) == 0

    def tree_size(self):
        stack = [self]
        count = 1
        while len(stack) > 0:
            node = stack.pop()
            children = node.children
            if children is not None:
                stack.extend(children)
                count += len(children)
        return count

    def add_child(self, node):
        node.path = self.path + (self,)
        node.parent = self
        self.children.append(node)

    def remove_child(self, node):
        node.path = ()
        node.parent = None
        self.children.remove(node)

    # Tree management abstract methods
    # --------------------------------
    def copy(self):
        """Create a new node representing a copy of the node's state.

        This method should create a new "blank" node using ``clone = TreeNode.copy(self)``,
        which takes care of copying generic MCTS node attributes, and should then fill in the
        domain-specific data by shallow- or deep-copying the custom attributes that were
        previously defined in :meth:`root`. Note that some attributes should be unique for each
        node (hence copied deeply), while others can (and should, if possible) be shared among
        all nodes. This should be analyzed on a case-by-case basis.

        Returns:
            TreeNode: a clone of the current node.
        """
        cls = type(self)
        clone = cls.__new__(cls)
        TreeNode.__init__(clone)
        return clone

    def branches(self):
        """Generate a collection of branch objects that are available from the current node.

        This method should produce a collection (*e.g* list, tuple, set, generator) of branch
        objects. A branch object is an object (of any type, and with any internal structure)
        which carries enough information to apply a modification (through :meth:`apply`) to a
        copy of the current node and obtain one of its child nodes. In some cases, a branch
        object may be something as simple as a boolean value (see *e.g.* the knapsack example).

        Returns:
            collection of branch objects.
        """
        raise NotImplementedError()

    def apply(self, branch):
        """Mutate the node's state by applying a branch (as produced by :meth:`branches`).

        The logic in this method is highly dependent on the internal structure of the nodes and
        branch objects that are returned by :meth:`branches`.

        Note:
            This method should operate in-place on the node. The :meth:`expand` method will take
            care of creating copies of the current node and calling :meth:`apply` on the copies,
            passing each branch object returned by :meth:`branches` and thereby generating the
            list of the current node's children.

        Parameters:
            branch: an object which should contain enough information to apply a local
                modification to (a copy of) the current node, such that the end result represents
                descending one level in the tree.
        """
        raise NotImplementedError()

    # This parameter controls interleaved selection of still-expanding parent nodes with their
    # children, thereby allowing the search to deepen without forcing the full expansion of all
    # ancestors. Turn off to force parents to be fully expanded before starting to select their
    # children.
    SELECTION_ALLOW_INTERLEAVING = False

    # MCTS-related methods
    def select(self, sols):
        """Pick the most favorable node for exploration.

        This method starts at the root and descends until a leaf is found. In each level the child
        to descend to is the one with the best selection score.
        """
        # Check if tree has been completely explored.
        if self.is_exhausted:
            return None
        # Go down the tree picking the best child at each step.
        curr_node = None
        next_node = self
        allow_interleaving = self.SELECTION_ALLOW_INTERLEAVING
        while next_node is not curr_node:
            curr_node = next_node
            curr_expansion = curr_node.expansion
            if not curr_expansion.is_started:
                break
            if curr_expansion.is_finished:
                cands = curr_node.children
            elif allow_interleaving:
                cands = itertools.chain(curr_node.children, [curr_node])
            else:
                break
            best_cands = max_elems(cands, key=lambda n: n.selection_score(sols))
            next_node = best_cands[0] if len(best_cands) == 1 else random.choice(best_cands)
        # TODO: remove the debug lines below
        #     if curr_expansion.is_finished:
        #         print(".", end="")
        #     elif next_node is curr_node:
        #         print("=", end="")
        #     else:
        #         print("!", end="")
        # print("  ", end="")
        # import sys
        # sys.stdout.flush()
        return curr_node

    def selection_score(self, sols):
        """Selection score uses an adapted UTC formula to balance exploration and exploitation.

        See https://en.wikipedia.org/wiki/Monte_Carlo_tree_search. The exploitation term has been
        adapted to the optimization context, where there is no concept of win ratio.
        """
        if self.sim_best.is_feas:
            z_node = self.sim_best.value
            z_best = sols.feas_best.value
            z_worst = sols.feas_worst.value
            min_exploit = sols.infeas_count / (sols.feas_count + sols.infeas_count)
            max_exploit = 1.0
        else:
            z_node = self.sim_best.value.infeas
            z_best = sols.infeas_best.value.infeas
            z_worst = sols.infeas_worst.value.infeas
            min_exploit = 0.0
            max_exploit = sols.infeas_count / (1 + sols.feas_count + sols.infeas_count)
        if z_best == z_worst:
            raw_exploit = 0.0
        else:
            raw_exploit = (z_worst - z_node) / (z_worst - z_best)
            assert 0.0 <= raw_exploit <= 1.0
        exploit = min_exploit + raw_exploit * (max_exploit - min_exploit)
        explore = (
            INF if self.parent is None else
            sqrt(2.0 * log(self.parent.sim_count) / self.sim_count)
        )
        expand = 1.0 / (1.0 + self.depth)
        return exploit + explore + expand

    # Parameter controlling how many child nodes (at most) are created during each iteration. The
    # default value is 1, which means that nodes are expanded one child at a time. This allows
    # the algorithm to pick other sites for exploration if the initial children of the current
    # node reveal it to be a bad choice.
    EXPANSION_LIMIT = 1

    def expand(self, pruning, cutoff):
        """Generate and link the children of this node.

        Note:
            The current implementation only creates at most 'EXPANSION_LIMIT' nodes.

        Returns:
            A list of newly created child nodes.
        """
        expansion = self.expansion
        if not expansion.is_started:
            assert self.children is None
            self.children = []
            expansion.start()
        new_children = []
        for _ in range(self.EXPANSION_LIMIT):
            if expansion.is_finished:
                break
            child = expansion.next()
            if pruning and child.bound() >= cutoff:
                continue
            self.add_child(child)
            new_children.append(child)
        return new_children

    def simulate(self):
        """Run a simulation from the current node to completion or infeasibility.

        This method defines the simulation strategy that is used to obtain node value estimates
        in MCTS. It should quickly descend the tree until a leaf node (solution or infeasibility)
        is reached, and return the result encountered.

        Smarter simulation strategies incorporate more domain-specific knowledge and normally use
        more computational resources, but can dramatically improve the performance of the
        algorithm. However, if the computational cost is too high, MCTS may be unable to gather
        enough data to improve the accuracy of its node value estimates, and will therefore end
        up wasting time in uninteresting regions. For best results, a balance between these
        conflicting goals must be reached.

        Returns:
            Solution: object containing the objective function value (or an :class:`Infeasible`
            value) and *optional* solution data.
        """
        raise NotImplementedError()

    def backpropagate(self, sol):
        """Integrate the solution obtained by this node's simulation into its subtree.

        This updates sim_count and sim_best in all ancestor nodes.
        """
        assert self.sim_count == 0
        self.sim_count = 1
        self.sim_sol = sol
        self.sim_best = sol
        for ancestor in self.path:
            ancestor.sim_count += 1
            if ancestor.sim_best.value > sol.value:
                ancestor.sim_best = sol

    def delete(self):
        """Remove a leaf or an entire subtree from the search tree, updating its ancestors' stats.

        This method unlinks the node from its parent, and also removes its simulation result from
        all the nodes in its path, which is roughly equivalent to the opposite of backpropagate().
        Note that nodes in the path *must* be updated in bottom-up order.
        Note also that deletion of a node may trigger the deletion of its parent.
        """
        node = self
        while True:
            # Keep references to the path and parent since they'd be lost after remove_child().
            bottom_up_path = reversed(node.path)
            parent = node.parent
            # Unlink node from parent.
            if parent is not None:
                parent.remove_child(node)
            # Update sim_best for all ancestor nodes (bottom-up order!).
            for ancestor in bottom_up_path:
                if ancestor.sim_best is not node.sim_best:
                    break
                # New ancestor sim_best is the best of children's sim_best or its own sim_sol.
                candidates = [child.sim_best for child in ancestor.children]
                candidates.append(ancestor.sim_sol)
                ancestor.sim_best = min(candidates, key=lambda s: s.value)
            # Propagate deletion to parent if it exists (true for all nodes except root) and has
            # become exhausted (i.e. is fully expanded and has no more children).
            if parent is None or not parent.is_exhausted:
                break
            node = parent

    # Branch-and-bound/pruning- related methods
    def prune(self, cutoff):
        """Called on the root node to prune off nodes/subtrees which can no longer lead to a
        solution better than the best solution found so far.
        """
        stack = [self]
        while len(stack) > 0:
            node = stack.pop()
            if node.bound() >= cutoff:
                node.delete()
            elif node.is_expanded:
                stack.extend(node.children)

    def bound(self):
        """Compute a lower bound on the current subtree's optimal objective value.

        A :meth:`bound` method shoud be defined in subclasses intending to use pruning. By
        default, pruning will be automatically activated if the root node defines a :meth:`bound`
        method different from the one defined in the base :class:`TreeNode` class.

        Returns:
            a lower bound on the optimal objective function value in the subtree under the
            current node.
        """
        raise NotImplementedError()
