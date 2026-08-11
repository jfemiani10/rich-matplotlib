"""Tests for the _RichPyplot proxy object."""

import io

import matplotlib.pyplot as plt
import pytest
from rich.console import Console

from rich_matplotlib._core import _RichPyplot


@pytest.fixture
def console_output():
    """A rich console that writes into a string buffer instead of the terminal."""
    buffer = io.StringIO()
    return Console(file=buffer, width=40), buffer


@pytest.fixture
def proxy(console_output):
    """A proxy that treats every currently open figure as pre-existing."""
    console, _ = console_output
    return _RichPyplot(console, set(plt.get_fignums()), width=20)


def test_unknown_attributes_come_from_pyplot(proxy):
    assert proxy.plot is plt.plot
    assert proxy.title is plt.title
    assert proxy.rcParams is plt.rcParams


def test_show_is_not_forwarded_to_pyplot(proxy):
    """The whole point of the proxy: show() must be ours, not matplotlib's."""
    assert proxy.show != plt.show


def test_missing_attributes_still_raise(proxy):
    with pytest.raises(AttributeError):
        getattr(proxy, "definitely_not_a_pyplot_function")  # noqa: B009


def test_show_renders_new_figures(proxy, console_output):
    _, buffer = console_output

    plt.figure()
    plt.plot([1, 2, 3], [4, 5, 6])
    proxy.show()

    assert buffer.getvalue() != ""


def test_show_closes_figures_by_default(proxy):
    plt.figure()
    proxy.show()

    assert plt.get_fignums() == []


def test_show_can_keep_figures_open(proxy):
    number = plt.figure().number
    proxy.show(close=False)

    assert number in plt.get_fignums()


def test_show_ignores_pyplot_arguments(proxy):
    """Existing code calling plt.show(block=False) must not break."""
    plt.figure()
    proxy.show(block=False)

    assert plt.get_fignums() == []


def test_pre_existing_figures_are_left_alone(console_output):
    console, buffer = console_output

    untouched = plt.figure().number
    proxy = _RichPyplot(console, set(plt.get_fignums()), width=20)
    proxy.show()

    assert untouched in plt.get_fignums()
    assert buffer.getvalue() == ""


def test_show_renders_figures_in_order(proxy, monkeypatch):
    rendered = []
    monkeypatch.setattr(_RichPyplot, "_render", lambda self, figure: rendered.append(figure.number))

    first = plt.figure().number
    second = plt.figure().number
    plt.figure(first)  # make an earlier figure current again
    proxy.show()

    assert rendered == [first, second]
