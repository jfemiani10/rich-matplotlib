"""Tests for the richplot() context manager and the terminal-matching style."""

import io

import matplotlib as mpl
import matplotlib.pyplot as plt
import pytest
from rich.console import Console

from rich_matplotlib import _core
from rich_matplotlib._core import _is_light, _terminal_style, richplot

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
VSCODE_DARK = (30, 30, 30)


@pytest.fixture
def console_output():
    """A rich console that writes into a string buffer instead of the terminal."""
    buffer = io.StringIO()
    return Console(file=buffer, width=40), buffer


@pytest.fixture(autouse=True)
def no_terminal_query(monkeypatch):
    """Never let the tests block on a real terminal that will not answer."""
    monkeypatch.setattr(_core, "terminal_background", lambda *a, **kw: None)


@pytest.mark.parametrize(
    ("color", "expected"),
    [
        (BLACK, False),
        (WHITE, True),
        (VSCODE_DARK, False),
        ((0, 0, 255), False),  # pure blue is dark despite a maxed-out channel
        ((0, 255, 0), True),  # pure green is not, because the eye favours green
    ],
)
def test_is_light_uses_perceived_brightness(color, expected):
    assert _is_light(color) is expected


def test_terminal_style_paints_the_background_color():
    with _terminal_style(VSCODE_DARK):
        assert mpl.rcParams["figure.facecolor"] == "#1e1e1e"
        assert mpl.rcParams["savefig.facecolor"] == "#1e1e1e"


def test_terminal_style_lightens_ink_on_dark_terminals():
    default_text = mpl.rcParams["text.color"]

    with _terminal_style(BLACK):
        assert mpl.rcParams["text.color"] != default_text


def test_terminal_style_leaves_light_terminals_alone():
    default_text = mpl.rcParams["text.color"]

    with _terminal_style(WHITE):
        assert mpl.rcParams["text.color"] == default_text


def test_terminal_style_restores_rcparams():
    before = dict(mpl.rcParams)

    with _terminal_style(BLACK):
        pass

    assert mpl.rcParams["figure.facecolor"] == before["figure.facecolor"]
    assert mpl.rcParams["text.color"] == before["text.color"]


def test_terminal_style_restores_rcparams_after_an_exception():
    before = mpl.rcParams["figure.facecolor"]

    with pytest.raises(RuntimeError), _terminal_style(BLACK):
        raise RuntimeError("boom")

    assert mpl.rcParams["figure.facecolor"] == before


def test_terminal_style_is_a_no_op_without_a_color():
    before = dict(mpl.rcParams)

    with _terminal_style(None):
        assert mpl.rcParams["figure.facecolor"] == before["figure.facecolor"]
        assert mpl.rcParams["text.color"] == before["text.color"]


def test_richplot_yields_a_pyplot_stand_in(console_output):
    console, _ = console_output

    with richplot(console=console) as rplt:
        assert rplt.plot is plt.plot


def test_richplot_renders_figures_on_exit(console_output):
    console, buffer = console_output

    with richplot(console=console, width=20) as rplt:
        rplt.figure()
        rplt.plot([1, 2, 3], [4, 5, 6])

    assert buffer.getvalue() != ""
    assert plt.get_fignums() == []


def test_richplot_does_not_reprint_an_explicitly_shown_figure(console_output):
    console, buffer = console_output

    with richplot(console=console, width=20) as rplt:
        rplt.figure()
        rplt.show()
        printed_inside = buffer.getvalue()

    assert buffer.getvalue() == printed_inside


def test_richplot_leaves_pre_existing_figures_alone(console_output):
    console, buffer = console_output
    untouched = plt.figure().number

    with richplot(console=console, width=20):
        pass

    assert untouched in plt.get_fignums()
    assert buffer.getvalue() == ""


def test_richplot_skips_rendering_when_the_body_raises(console_output):
    console, buffer = console_output

    with pytest.raises(RuntimeError), richplot(console=console, width=20) as rplt:
        rplt.figure()
        raise RuntimeError("boom")

    assert buffer.getvalue() == ""


def test_richplot_can_skip_querying_the_terminal(monkeypatch):
    """match_background=False must not cost a terminal round trip."""
    queried = False

    def spy(*args, **kwargs):
        nonlocal queried
        queried = True
        return None

    monkeypatch.setattr(_core, "terminal_background", spy)

    with richplot(console=Console(file=io.StringIO()), match_background=False):
        pass

    assert queried is False
