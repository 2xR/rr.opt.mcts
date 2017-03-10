from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import functools
from matplotlib import pyplot

from .infeasible import Infeasible


def layout(root, x_min=0.02, x_max=0.98, y_min=0.02, y_max=0.98):
    tree_height = root.tree_height()
    if tree_height < 2:
        raise Exception("argument tree must have at least two levels")
    x_span = {root: (x_min, x_max)}
    coords = {}
    for node in root.iter_preorder():
        x_min, x_max = x_span[node]
        x = (x_min + x_max) / 2.0
        y = y_max - node.depth / (tree_height - 1.0) * (y_max - y_min)
        coords[node] = (x, y)
        if len(node.children) > 0:
            child_width = (x_max - x_min) / len(node.children)
            for i, child in enumerate(node.children):
                x_span[child] = (x_min + i*child_width, x_min + (i+1)*child_width)
    return coords


def paint(root, raw_score, norm_score, colormap="jet", default_color=(0.0, 0.0, 0.0, 1.0)):
    score_func = norm_score({node: raw_score(node) for node in root.iter_preorder()})
    cmap = pyplot.get_cmap(colormap)
    color = {}
    for node in root.iter_preorder():
        if node.parent is None:
            continue
        score = score_func(node)
        color[node] = default_color if score is None else cmap(score)
        assert score is None or 0.0 <= score <= 1.0
    return color


def _global_score_normalizer(raw_score):
    valid_scores = [s for s in raw_score.values() if s is not None]
    if len(valid_scores) == 0:
        max_score = min_score = 0.0
    else:
        max_score = max(valid_scores)
        min_score = min(valid_scores)
    delta_score = max_score - min_score

    def global_normalizer(node):
        score = raw_score[node]
        if score is None:
            return None
        return 0.5 if delta_score == 0.0 else (score - min_score) / delta_score

    return global_normalizer


def _local_score_normalizer(raw_score):
    local_scores_interval = {}
    for node in raw_score.keys():
        if len(node.children) > 0:
            local_scores = [raw_score[c] for c in node.children if raw_score[c] is not None]
            if len(local_scores) > 0:
                local_scores_interval[node] = (min(local_scores), max(local_scores))

    def local_normalizer(node):
        score = raw_score[node]
        if score is None:
            return None
        min_score, max_score = local_scores_interval[node.parent]
        delta_score = max_score - min_score
        return 0.5 if delta_score == 0.0 else (score - min_score) / delta_score

    return local_normalizer


def _objective_score(node):
    z = node.stats.overall.best.value
    return None if isinstance(z, Infeasible) else -z


paint.by_objective = functools.partial(
    paint,
    raw_score=_objective_score,
    norm_score=_global_score_normalizer,
)
paint.by_selection = functools.partial(
    paint,
    raw_score=lambda n: n.selection_score(),
    norm_score=_local_score_normalizer,
)
paint.by_exploitation = functools.partial(
    paint,
    raw_score=lambda n: n.stats.opt_exploitation_score(),
    norm_score=_local_score_normalizer,
)
paint.by_exploration = functools.partial(
    paint,
    raw_score=lambda n: n.stats.uct_exploration_score(),
    norm_score=_local_score_normalizer,
)


def draw(root, color=paint.by_objective, coords=None, highlight_paths=(), axes=None, show=True):
    """Display a tree with color-coded edges."""
    # Create a new pair of axes if necessary.
    if axes is None:
        fig = pyplot.figure()
        axes = fig.add_subplot(1, 1, 1)
    # Compute node colors and positions if necessary.
    if callable(color):
        color = color(root)
    if coords is None:
        coords = layout(root)
    # Draw the actual tree and path highlights.
    _draw_tree(axes, coords, color)
    _draw_highlights(axes, coords, highlight_paths)
    # Configure the axes to show the [0, 1] x [0, 1] region and display no ticks.
    axes.set_xlim(0, 1)
    axes.set_ylim(0, 1)
    axes.set_xticks([])
    axes.set_yticks([])
    if show:
        pyplot.interactive(True)
        pyplot.show()
    return axes


def _draw_tree(axes, coords, color):
    for n, c in color.items():
        x0, y0 = coords[n.parent]
        x1, y1 = coords[n]
        axes.plot([x0, x1], [y0, y1], color=c)


def _draw_highlights(axes, coords, paths):
    for path in paths:
        XYs = [coords[v] for v in path]
        Xs = [xy[0] for xy in XYs]
        Ys = [xy[1] for xy in XYs]
        axes.plot(
            Xs, Ys,
            color="black",
            linewidth=5,
            dashes=[5, 15],
            marker="o",
            markersize=5,
            markerfacecolor="black",
            markeredgewidth=0,
            zorder=1,
        )
