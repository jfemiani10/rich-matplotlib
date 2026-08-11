"""Compare a figure that blends into the terminal with one that does not.

Run it from the project root with::

    python demos/background_matching.py

The first plot keeps matplotlib's white canvas and sits in the terminal as an obvious
white rectangle. The second asks the terminal for its background color (OSC 11) and
paints the figure to match, so only the ink is visible. The difference is dramatic on
a dark theme and invisible on a white one -- which is the point.
"""

import numpy as np
from rich.console import Console

from rich_matplotlib import richplot, terminal_background


def report(console: Console) -> None:
    """Print what the terminal said about its background color.

    Args:
        console: The console to print the report to.
    """
    color = terminal_background()

    if color is None:
        console.print(
            "[yellow]No background color reported.[/] Either this is not a terminal "
            "(piped output, CI) or it ignores OSC 11. Figures keep their default style.",
        )
        return

    red, green, blue = color
    swatch = f"#{red:02x}{green:02x}{blue:02x}"
    console.print(f"Terminal background: [b]{swatch}[/] rgb{color} [on {swatch}]      [/]")


def plot_wave(plt, title: str) -> None:
    """Draw the same figure both times, so only the styling differs.

    Args:
        plt: The pyplot stand-in yielded by ``richplot``.
        title: Title to put on the figure.
    """
    x = np.linspace(0, 4 * np.pi, 400)

    plt.figure(figsize=(8, 2.5))
    plt.plot(x, np.sin(x), label="sin(x)")
    plt.plot(x, np.sin(x) * np.exp(-x / 10), label="damped")
    plt.legend(loc="upper right")
    plt.title(title)
    plt.grid(alpha=0.3)


def main() -> None:
    """Render the same plot with and without terminal background matching."""
    console = Console()
    report(console)

    console.rule("match_background=False")
    with richplot(console=console, match_background=False) as plt:
        plot_wave(plt, "default matplotlib style")

    console.rule("match_background=True")
    with richplot(console=console, match_background=True) as plt:
        plot_wave(plt, "styled to match the terminal")


if __name__ == "__main__":
    main()
