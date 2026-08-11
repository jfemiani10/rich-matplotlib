"""Share one rich Console between a progress bar, a table, and a plot.

Run it from the project root with::

    python demos/rich_composition.py

This is the reason ``richplot`` renders through rich instead of writing escape codes
to stdout itself. A rich live display (progress bar, spinner, status) owns the cursor
while it is running; anything that prints behind its back gets overwritten or shredded.
Passing the *same* Console to ``richplot`` lets rich sequence the two properly.
"""

import time

import numpy as np
from rich.console import Console
from rich.progress import Progress
from rich.table import Table

from rich_matplotlib import richplot

STEPS = 40


def simulate(console: Console) -> np.ndarray:
    """Pretend to do expensive work, reporting progress on the shared console.

    Args:
        console: The console the progress bar draws on.

    Returns:
        One noisy sample per step.
    """
    samples = np.empty(STEPS)
    rng = np.random.default_rng(seed=0)

    with Progress(console=console) as progress:
        task = progress.add_task("Simulating...", total=STEPS)

        for step in range(STEPS):
            samples[step] = np.sin(step / 5) + rng.normal(scale=0.2)
            time.sleep(0.02)
            progress.advance(task)

    return samples


def summarize(samples: np.ndarray) -> Table:
    """Build a small rich table of summary statistics.

    Args:
        samples: The simulated values.

    Returns:
        A table ready to print to a console.
    """
    table = Table(title="Sample statistics")
    table.add_column("Statistic")
    table.add_column("Value", justify="right")

    for name, value in [("min", samples.min()), ("mean", samples.mean()), ("max", samples.max())]:
        table.add_row(name, f"{value:.3f}")

    return table


def main() -> None:
    """Run the simulation, then print its results and its plot to one console."""
    console = Console()

    samples = simulate(console)
    console.print(summarize(samples))

    # The same console object, so the plot lands below the table rather than
    # racing it for the cursor.
    with richplot(console=console, width="80%") as plt:
        plt.figure(figsize=(8, 3))
        plt.plot(samples, marker="o", markersize=3, linewidth=1)
        plt.axhline(samples.mean(), color="tab:red", linestyle="--", label="mean")
        plt.legend(loc="upper right")
        plt.title("Simulated samples")
        plt.grid(alpha=0.3)


if __name__ == "__main__":
    main()
