"""Plots scrolling past a progress bar that stays pinned to the bottom of the screen.

Run it from the project root with::

    python demos/rich_composition.py

This is the reason ``richplot`` renders through rich instead of writing escape codes to
stdout itself. A rich live display (progress bar, spinner, status) owns the bottom of the
terminal and redraws it continuously; anything that prints behind its back gets
overwritten or shredded. That is exactly what happens when a sixel *backend* and a
progress bar share a terminal.

Passing the *same* Console to ``richplot`` lets rich sequence the two. Everything printed
inside the ``Progress`` block scrolls up above the bar, so this demo can finish a stage,
draw its figure, and carry on with the bar still sitting where it was.
"""

import time

import numpy as np
from rich.console import Console
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn
from rich.table import Table

from rich_matplotlib import richplot

#: Steps of "work" per stage. Each one advances the bar and sleeps.
STEPS_PER_STAGE = 25

#: Seconds per step, slow enough that the bar is visibly moving rather than flashing past.
STEP_DELAY = 0.04

#: Seconds to leave each finished plot on screen before the next stage starts.
PLOT_DELAY = 1.0


def signal(name: str, steps: int, rng: np.random.Generator) -> np.ndarray:
    """Generate one stage's worth of noisy samples.

    Args:
        name: Which shape to generate: ``"ramp"``, ``"wave"``, ``"decay"`` or ``"step"``.
        steps: How many samples to produce.
        rng: The random generator supplying the noise.

    Returns:
        One noisy sample per step.
    """
    t = np.linspace(0, 1, steps)
    shapes = {
        "ramp": 2 * t,
        "wave": np.sin(4 * np.pi * t),
        "decay": np.exp(-3 * t),
        "step": (t > 0.5).astype(float),
    }
    return shapes[name] + rng.normal(scale=0.12, size=steps)


def run_stage(name: str, progress: Progress, rng: np.random.Generator) -> np.ndarray:
    """Run one stage: advance the progress bar step by step, then plot the result.

    The plot is drawn *inside* the ``Progress`` block on purpose. Rich prints it above
    the live region, so the bar never moves and never gets scribbled over.

    Args:
        name: The stage name, used for the task label and the plot title.
        progress: The live progress display, already started.
        rng: The random generator supplying the noise.

    Returns:
        The samples this stage produced.
    """
    task = progress.add_task(f"{name}...", total=STEPS_PER_STAGE)
    samples = signal(name, STEPS_PER_STAGE, rng)

    for _ in range(STEPS_PER_STAGE):
        time.sleep(STEP_DELAY)
        progress.advance(task)

    # Same console as the progress bar, so this lands above it rather than through it.
    with richplot(console=progress.console, width="60%") as plt:
        plt.figure(figsize=(8, 3))
        plt.plot(samples, marker="o", markersize=3, linewidth=1)
        plt.axhline(samples.mean(), color="tab:red", linestyle="--", label="mean")
        plt.legend(loc="upper right")
        plt.title(f"stage: {name}")
        plt.grid(alpha=0.3)

    # A beat before the next stage, so the plots do not all arrive at once.
    time.sleep(PLOT_DELAY)
    return samples


def summarize(results: dict[str, np.ndarray]) -> Table:
    """Build a rich table of summary statistics, one row per stage.

    Args:
        results: The samples each stage produced, keyed by stage name.

    Returns:
        A table ready to print to a console.
    """
    table = Table(title="Stage statistics")
    table.add_column("Stage")
    for column in ("min", "mean", "max"):
        table.add_column(column, justify="right")

    for name, samples in results.items():
        table.add_row(name, *(f"{v:.3f}" for v in (samples.min(), samples.mean(), samples.max())))

    return table


def main() -> None:
    """Run four stages under one progress display, plotting each as it finishes."""
    console = Console()
    rng = np.random.default_rng(seed=0)
    results: dict[str, np.ndarray] = {}

    console.print("[bold]Four stages, four plots, one progress bar.[/bold]")
    console.print("Watch the bar stay at the bottom while the plots scroll past it.\n")

    # A bar with an elapsed-time column, so it is obvious it keeps ticking while the
    # plots are being drawn above it.
    columns = (
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
    )

    with Progress(*columns, console=console) as progress:
        for name in ("ramp", "wave", "decay", "step"):
            results[name] = run_stage(name, progress, rng)

    # Outside the Progress block now: the bar is gone and this is an ordinary print.
    console.print(summarize(results))

    # One last figure comparing every stage, to show that several plots in a single
    # block are rendered in the order they were created.
    with richplot(console=console, width="70%") as plt:
        plt.figure(figsize=(8, 4))
        for name, samples in results.items():
            plt.plot(samples, linewidth=1, label=name)
        plt.legend(loc="upper right", ncols=2)
        plt.title("All stages")
        plt.grid(alpha=0.3)


if __name__ == "__main__":
    main()
