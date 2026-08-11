"""Smallest end-to-end demo: draw one figure straight into the terminal.

Run it from the project root with::

    python demos/basic_plot.py

Best viewed in a terminal with sixel or Kitty graphics support (foot, WezTerm,
Konsole, mlterm, Windows Terminal, or xterm built with sixel enabled). Anywhere
else -- including piping this into a file -- it degrades to unicode blocks instead
of failing, which is exactly the behaviour worth seeing at least once.
"""

import numpy as np

from rich_matplotlib import richplot


def main() -> None:
    """Plot two waves and let the context manager render them on exit."""
    x = np.linspace(0, 4 * np.pi, 400)

    # Inside the block, `plt` is the proxy rather than matplotlib.pyplot itself,
    # so no window is opened and no explicit show() is needed.
    with richplot() as plt:
        plt.figure(figsize=(8, 4))
        plt.plot(x, np.sin(x), label="sin(x)")
        plt.plot(x, np.cos(x), label="cos(x)")
        plt.legend(loc="upper right")
        plt.title("Hello from the terminal")
        plt.xlabel("x")
        plt.grid(alpha=0.3)


if __name__ == "__main__":
    main()
