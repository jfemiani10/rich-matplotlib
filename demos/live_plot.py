"""Animate a sine wave in place, by redrawing one figure inside a rich ``Live`` display.

Run it from the project root with::

    python demos/live_plot.py

``richplot`` *prints* figures, which is what a script wants: each plot lands in the
scrollback under the text above it. An animation wants the opposite -- one figure,
repainted where it already is.

That is what :func:`figure_image` is for. It performs the same conversion ``richplot``
does internally (figure to PNG to terminal image) but hands the result back as a rich
renderable instead of printing it, so ``Live`` can redraw it every frame.

Two details make the difference between an animation and a flicker:

* The figure is created once and only its y-data is replaced each frame. Rebuilding the
  whole figure per frame is slower and, worse, lets matplotlib rescale the axes so the
  plot jitters.
* The axis limits are pinned, for the same reason.

The frame rate is bounded by how long ``savefig`` plus the terminal's own image decoding
take, so treat ``FRAME_DELAY`` as a floor rather than a promise.
"""

import time

import matplotlib.pyplot as plt
import numpy as np
from rich.console import Console
from rich.live import Live

from rich_matplotlib import figure_image, terminal_background, terminal_style

#: How many frames to draw. At the default delay this is a few seconds of animation.
FRAMES = 150

#: Seconds to wait between frames, on top of however long rendering takes.
FRAME_DELAY = 0

#: Radians the wave shifts per frame. One full cycle every 50 frames.
PHASE_STEP = 2 * np.pi / 50


def build_figure(x: np.ndarray):
    """Create the figure that every frame will reuse.

    Args:
        x: The x values the wave is sampled at.

    Returns:
        A ``(figure, line)`` pair. The line is what each frame updates.
    """
    figure = plt.figure(figsize=(8, 3))
    (line,) = plt.plot(x, np.sin(x), linewidth=2)

    # Pinned so the axes do not rescale as the wave slides, which would make the whole
    # image twitch between frames.
    plt.ylim(-1.2, 1.2)
    plt.xlim(x[0], x[-1])
    plt.title("sin(x + phase)")
    plt.xlabel("x")
    plt.grid(alpha=0.3)
    figure.tight_layout()

    return figure, line


def main() -> None:
    """Slide a sine wave across the terminal until it finishes or you interrupt it."""
    console = Console()
    console.print("[bold]A sine wave with a shifting phase.[/bold]")
    console.print("Rendered in place with rich Live. Ctrl-C to stop early.\n")

    x = np.linspace(0, 4 * np.pi, 400)

    # The styling has to be active while the figure is *created*, not just while it is
    # saved, so the whole animation runs inside it. richplot does this for you; here the
    # figure is built by hand, so the demo does it by hand too.
    with terminal_style(terminal_background()):
        figure, line = build_figure(x)

        try:
            # auto_refresh off because every repaint is driven by an update below;
            # letting Live also refresh on a timer would just re-encode the same image.
            with Live(console=console, auto_refresh=False) as live:
                for frame in range(FRAMES):
                    line.set_ydata(np.sin(x + frame * PHASE_STEP))
                    live.update(figure_image(figure, width="70%"), refresh=True)
                    time.sleep(FRAME_DELAY)
        except KeyboardInterrupt:
            console.print("\nstopped")
        finally:
            # figure_image never closes anything, so the one figure this demo opened is
            # this demo's to clean up.
            plt.close(figure)


if __name__ == "__main__":
    main()
