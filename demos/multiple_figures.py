"""Several figures in one block, plus control over when they are rendered.

Run it from the project root with::

    python demos/multiple_figures.py

Shows three things: figures are rendered in the order they were *created*, not the
order they were last touched; ``show()`` can be called early to render mid-block; and
``close=False`` keeps a figure open so it can be added to and rendered again.
"""

import numpy as np

from rich_matplotlib import richplot


def main() -> None:
    """Render three figures, one of them twice."""
    x = np.linspace(0, 2 * np.pi, 200)

    with richplot(width="60%") as plt:
        # Created first, so rendered first -- even though it is drawn on last.
        first = plt.figure(figsize=(7, 2.5))
        plt.title("figure 1: filled in later")

        plt.figure(figsize=(7, 2.5))
        plt.plot(x, np.sin(x), color="tab:orange")
        plt.title("figure 2")

        # Switching back to an earlier figure makes it current again; it does not
        # move it to the back of the queue.
        plt.figure(first)
        plt.plot(x, x * np.sin(x), color="tab:blue")

        # Renders figures 1 and 2 now, then closes them, so the block's automatic
        # render on exit only has the third figure left to deal with.
        plt.show()

        plt.figure(figsize=(7, 2.5))
        plt.plot(x, np.sqrt(x), color="tab:green")
        plt.title("figure 3: rendered on exit")


if __name__ == "__main__":
    main()
