"""Tests for how a figure's size is translated into terminal cells.

These guard the property that matters to the eye: a figure must reach the terminal with
the shape it was drawn with. The arithmetic lives in textual-image, so the tests go
through the same ``ImageSize`` it uses rather than re-deriving it here.
"""

import io

import matplotlib.pyplot as plt
import pytest
from rich.console import Console
from textual_image._geometry import ImageSize
from textual_image._terminal import CellSize

from rich_matplotlib._core import _RichPyplot, richplot

#: A typical terminal cell, in pixels. Cells are about twice as tall as they are wide,
#: which is why cell counts say nothing about shape on their own.
CELL = CellSize(width=10, height=20)

#: Console size, in cells, that the aspect-ratio tests measure against.
CONSOLE_COLUMNS = 120
CONSOLE_ROWS = 40

#: Widest a rendered figure may be off its original aspect ratio, as a fraction. Some
#: error is unavoidable: a figure has to land on a whole number of cells, so a narrow
#: render has very little resolution to round to.
ASPECT_TOLERANCE = 0.07


def rendered_aspect(source: tuple[int, int], width, height) -> float:
    """Work out the aspect ratio a figure ends up with once sized for the terminal.

    Args:
        source: The figure's own size as ``(pixel_width, pixel_height)``.
        width: The width specification passed to the renderable.
        height: The height specification passed to the renderable.

    Returns:
        The width-to-height ratio of the image as it reaches the terminal.
    """
    size = ImageSize(*source, width, height)
    pixel_width, pixel_height = size.get_pixel_size(CONSOLE_COLUMNS, CONSOLE_ROWS, CELL)
    return pixel_width / pixel_height


@pytest.fixture
def console_output():
    """A rich console that writes into a string buffer instead of the terminal."""
    buffer = io.StringIO()
    return Console(file=buffer, width=40), buffer


@pytest.fixture
def sizes(monkeypatch):
    """Collect the (width, height) every figure is rendered at, instead of drawing it."""
    recorded = []
    monkeypatch.setattr(
        "rich_matplotlib._core.TerminalImage",
        lambda image, width, height: recorded.append((width, height)) or "",
    )
    return recorded


# 8x3 is the wide, short shape the README recommends; 6.4x4.8 is matplotlib's default;
# the square and tall cases are where an unconstrained height goes most wrong.
FIGURE_PIXELS = [
    pytest.param((800, 300), id="wide"),
    pytest.param((640, 480), id="matplotlib-default"),
    pytest.param((500, 500), id="square"),
    pytest.param((300, 900), id="tall"),
]


@pytest.mark.parametrize("source", FIGURE_PIXELS)
@pytest.mark.parametrize("width", ["auto", "100%", "60%"])
def test_auto_height_preserves_aspect_ratio(source, width):
    """The regression this module exists for: figures must not come out stretched."""
    original = source[0] / source[1]
    error = abs(rendered_aspect(source, width, "auto") / original - 1)

    assert error <= ASPECT_TOLERANCE


@pytest.mark.parametrize("source", FIGURE_PIXELS)
def test_unset_height_is_what_distorted_the_figure(source):
    """Documents why height=None is not a safe default, so nobody restores it."""
    original = source[0] / source[1]
    unset = rendered_aspect(source, "100%", None)

    # The wide case is the least affected, and even it is off by half.
    assert abs(unset / original - 1) > 0.4


def test_default_full_width_lets_a_tall_figure_overflow():
    """The trade-off the default accepts: full width, and whatever height that needs.

    A terminal scrolls vertically, so overflowing is not an error -- but it is worth
    pinning down, because it is the reason to reach for ``width="auto"`` instead.
    """
    tall = (300, 900)
    size = ImageSize(*tall, "100%", "auto")
    _, rows = size.get_cell_size(CONSOLE_COLUMNS, CONSOLE_ROWS, CELL)

    assert rows > CONSOLE_ROWS


def test_auto_width_keeps_a_tall_figure_on_one_screen():
    """Opting into "auto" on both axes trades width for fitting on one screen."""
    tall = (300, 900)
    size = ImageSize(*tall, "auto", "auto")
    _, rows = size.get_cell_size(CONSOLE_COLUMNS, CONSOLE_ROWS, CELL)

    assert rows <= CONSOLE_ROWS


def test_both_dimensions_reach_the_renderable(console_output, sizes):
    """Height must actually be forwarded, not dropped as it was before."""
    console, _ = console_output
    proxy = _RichPyplot(console, set(plt.get_fignums()), width="60%", height=12)

    plt.figure()
    proxy.show()

    assert sizes == [("60%", 12)]


def test_richplot_defaults_to_full_width_and_auto_height(console_output, sizes):
    """The default pair: fill the console's width, derive the height from it."""
    console, _ = console_output

    with richplot(console=console) as rplt:
        rplt.figure()

    assert sizes == [("100%", "auto")]


def test_richplot_forwards_an_explicit_size(console_output, sizes):
    console, _ = console_output

    with richplot(console=console, width="100%", height="50%") as rplt:
        rplt.figure()

    assert sizes == [("100%", "50%")]
