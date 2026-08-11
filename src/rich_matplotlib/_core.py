"""Render matplotlib figures as images inside a terminal, via rich and sixel graphics.

The main entry point is the :func:`richplot` context manager. Figures created inside
its scope are captured and printed to the terminal as images instead of being sent to
a GUI window:

    >>> from rich_matplotlib import richplot
    >>> with richplot() as plt:
    ...     plt.plot([1, 2, 3], [4, 5, 6])

Because rendering goes through a rich ``Console``, this composes with rich's live
displays (progress bars, tables) as long as the same console is used for both.

Requires a terminal with sixel graphics support (e.g. xterm with sixel enabled,
foot, WezTerm, Windows Terminal, mlterm, or Konsole).
"""

from __future__ import annotations

import re
import sys
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from io import BytesIO

import matplotlib.pyplot as plt
from PIL import Image as PILImage
from rich.console import Console
from textual_image import _terminal
from textual_image._terminal import TerminalError, capture_terminal_response

try:
    import termios
except ImportError:  # pragma: no cover - Windows has no termios module
    #: Extra exception types raised when putting the terminal into raw mode fails.
    _RAW_MODE_ERRORS: tuple[type[BaseException], ...] = ()
else:
    # termios.error derives from Exception, not OSError, so it needs naming explicitly.
    _RAW_MODE_ERRORS = (termios.error,)

#: Minimum seconds to allow for any terminal capability probe.
#:
#: textual-image hardcodes 0.1s, which is too short for terminals answering over SSH or
#: through a multiplexer. When that probe times out the terminal is misreported as having
#: no sixel support and rendering silently degrades to unicode blocks.
_MINIMUM_PROBE_TIMEOUT = 1.0


@contextmanager
def _minimum_probe_timeout(seconds: float) -> Iterator[None]:
    """Temporarily raise the timeout textual-image uses when probing the terminal.

    Patches ``textual_image._terminal.capture_terminal_response`` for the duration of
    the block and always restores the original afterwards, including on exception.

    Args:
        seconds: The shortest timeout any probe is allowed to use.

    Yields:
        None. The patch is active for the body of the ``with`` block.
    """
    original = _terminal.capture_terminal_response

    def patched(start_marker: str, end_marker: str, timeout: float | None = None):
        # ``None`` means "wait forever" upstream, which can hang on a silent terminal,
        # so an unset timeout becomes the minimum rather than staying unbounded.
        effective = seconds if timeout is None else max(timeout, seconds)
        return original(start_marker, end_marker, effective)

    _terminal.capture_terminal_response = patched
    try:
        yield
    finally:
        _terminal.capture_terminal_response = original


# Importing this module probes the terminal and picks a renderer once, at import time:
# sixel, then Kitty's graphics protocol, then colored half-blocks, then plain unicode.
# The probe must therefore happen with a workable timeout, hence the patch above.
with _minimum_probe_timeout(_MINIMUM_PROBE_TIMEOUT):
    from textual_image.renderable import Image as TerminalImage

#: Escape sequence that asks the terminal to report its background color (OSC 11).
_OSC11_QUERY = "\x1b]11;?\x1b\\"

#: Matches an OSC 11 reply such as ``\x1b]11;rgb:1e1e/1e1e/1e1e\x1b\\``.
#: Terminals are free to report each channel with a different number of hex digits,
#: so the component widths are deliberately not pinned down here.
_OSC11_REPLY = re.compile(
    r"\x1b\]11;rgb:([0-9a-fA-F]+)/([0-9a-fA-F]+)/([0-9a-fA-F]+)\x1b\\",
)


def _scale_to_byte(component: str) -> int:
    """Scale one hex color component of any width onto the 0-255 range.

    Terminals may answer OSC 11 with 1 to 4 hex digits per channel, so ``"ff"``,
    ``"ffff"`` and ``"f"`` all mean "fully saturated" and must map to 255.

    Args:
        component: A hex string for a single color channel, e.g. ``"1e1e"``.

    Returns:
        The channel value scaled to an integer in the range 0-255.
    """
    maximum = 16 ** len(component) - 1
    return round(int(component, 16) * 255 / maximum)


def _parse_osc11_reply(sequence: str) -> tuple[int, int, int] | None:
    """Parse a terminal's OSC 11 reply into an 8-bit RGB triple.

    Args:
        sequence: The raw reply captured from the terminal.

    Returns:
        The background color as ``(red, green, blue)`` in the range 0-255,
        or ``None`` if the reply was not a well-formed OSC 11 color report.
    """
    match = _OSC11_REPLY.fullmatch(sequence)
    if match is None:
        return None

    red, green, blue = match.groups()
    return _scale_to_byte(red), _scale_to_byte(green), _scale_to_byte(blue)


def _can_query_terminal() -> bool:
    """Report whether this process is attached to a terminal that can be queried.

    Querying requires writing to stdout *and* reading the reply from stdin, so both
    must be real terminals. When output is piped to a file, or the process runs under
    CI or a Jupyter kernel, they are not.

    Returns:
        True if it is safe to send the terminal a query and wait for a reply.
    """
    streams = (sys.__stdin__, sys.__stdout__)
    return all(stream is not None and stream.isatty() for stream in streams)


def terminal_background(timeout: float = 1.0) -> tuple[int, int, int] | None:
    """Ask the terminal for its background color, as 8-bit RGB.

    Sends an OSC 11 query and reads the reply. Terminals that do not support the
    query simply stay silent, which is why a timeout is needed to give up on them.

    Args:
        timeout: Seconds to wait for the terminal to respond.

    Returns:
        The background color as ``(red, green, blue)`` in the range 0-255, or
        ``None`` if there is no terminal to ask, the terminal did not answer, or it
        answered with something unparseable.
    """
    if not _can_query_terminal():
        return None

    try:
        with capture_terminal_response("\x1b]11;", "\x1b\\", timeout) as response:
            sys.__stdout__.write(_OSC11_QUERY)  # type: ignore[union-attr]
            sys.__stdout__.flush()  # type: ignore[union-attr]
    except (TerminalError, TimeoutError, *_RAW_MODE_ERRORS):
        return None

    return _parse_osc11_reply(response.sequence)


#: Perceived brightness (0-255) above which a background counts as a light theme.
#: Halfway up the scale, so only genuinely dark terminals get the dark style.
_LIGHT_BACKGROUND_THRESHOLD = 128


def _is_light(color: tuple[int, int, int]) -> bool:
    """Report whether a background color reads as light to the eye.

    Uses the ITU-R BT.601 luma weights rather than a plain average, because the eye is
    far more sensitive to green than to blue: pure blue is dark, pure green is not.

    Args:
        color: The background as ``(red, green, blue)`` in the range 0-255.

    Returns:
        True if plots should use dark ink on this background.
    """
    red, green, blue = color
    return 0.299 * red + 0.587 * green + 0.114 * blue > _LIGHT_BACKGROUND_THRESHOLD


@contextmanager
def _terminal_style(color: tuple[int, int, int] | None) -> Iterator[None]:
    """Style matplotlib to blend into a terminal of the given background color.

    Dark terminals additionally get matplotlib's ``dark_background`` style, which
    lightens the text, axes and default color cycle so they stay readable. The exact
    terminal color is then painted onto the figure so its edges disappear into the
    surrounding text rather than sitting in a visible box.

    Args:
        color: The terminal background as ``(red, green, blue)``, or ``None`` when it
            could not be determined, in which case matplotlib is left untouched.

    Yields:
        None. The styling is active for the body of the ``with`` block and is undone
        afterwards, including on exception.
    """
    if color is None:
        yield
        return

    background = "#{:02x}{:02x}{:02x}".format(*color)
    overrides = {
        "figure.facecolor": background,
        "axes.facecolor": background,
        # Without these, saving the PNG repaints the background white, undoing the above.
        "savefig.facecolor": background,
        "savefig.edgecolor": background,
    }

    with ExitStack() as stack:
        if not _is_light(color):
            stack.enter_context(plt.style.context("dark_background"))

        # Entered last so these win over anything the style set.
        stack.enter_context(plt.rc_context(overrides))
        yield


class _RichPyplot:
    """A stand-in for ``matplotlib.pyplot`` that prints figures to a rich console.

    Every attribute except :meth:`show` is forwarded straight to ``matplotlib.pyplot``,
    so this object can be used anywhere the real module would be. Only the figures
    created after this proxy was built are rendered, leaving any figures the caller
    already had open untouched.
    """

    def __init__(self, console: Console, initial_figures: set[int], width: int | str) -> None:
        """Initialize the proxy.

        Args:
            console: The rich console figures are printed to.
            initial_figures: Numbers of the figures that existed beforehand, which
                this proxy must leave alone.
            width: Width of the rendered image, either a number of terminal cells or a
                percentage string such as ``"100%"``.
        """
        self.console = console
        self.initial_figures = initial_figures
        self.width = width

    def __getattr__(self, name: str):
        """Forward any unknown attribute to ``matplotlib.pyplot``.

        Python only calls this for attributes that were not found the normal way, so
        :meth:`show` and the instance attributes above take precedence over the module.

        Args:
            name: The attribute being looked up.

        Returns:
            The corresponding attribute of ``matplotlib.pyplot``.
        """
        return getattr(plt, name)

    def _new_figure_numbers(self) -> list[int]:
        """Return the numbers of figures created since this proxy was built, in order."""
        return sorted(set(plt.get_fignums()) - self.initial_figures)

    def _render(self, figure) -> None:
        """Print a single figure to the console as a terminal image.

        The figure is encoded as an in-memory PNG rather than written to disk, then
        handed to textual-image for conversion into whatever the terminal supports.

        Args:
            figure: The matplotlib ``Figure`` to render.
        """
        with BytesIO() as buffer:
            figure.savefig(buffer, format="png")
            buffer.seek(0)

            with PILImage.open(buffer) as image:
                # PIL loads lazily, so the pixels must be copied out before the
                # underlying buffer is closed by these context managers.
                self.console.print(TerminalImage(image.copy(), width=self.width))

    def show(self, *_args, close: bool = True, **_kwargs) -> None:
        """Render every figure created inside the context.

        Replaces ``matplotlib.pyplot.show``. Positional and keyword arguments that the
        real ``show`` accepts (such as ``block``) are ignored, so existing code calling
        ``plt.show(block=False)`` keeps working.

        Args:
            close: Whether to close each figure once it has been rendered. Closing is
                the default so that repeated calls do not reprint the same figure.
        """
        for number in self._new_figure_numbers():
            figure = plt.figure(number)
            self._render(figure)

            if close:
                plt.close(figure)


@contextmanager
def richplot(
    console: Console | None = None,
    width: int | str = "100%",
    match_background: bool = True,
) -> Iterator[_RichPyplot]:
    """Draw matplotlib figures into the terminal instead of a GUI window.

    Yields a stand-in for ``matplotlib.pyplot``. Use it exactly like ``plt``; any
    figure still open when the block ends is rendered automatically, so an explicit
    ``show()`` is optional:

        >>> with richplot() as plt:  # doctest: +SKIP
        ...     plt.plot([1, 2, 3], [4, 5, 6])
        ...     plt.title("rendered in the terminal")

    Args:
        console: The rich console to print to. Pass the console a live display or
            progress bar is using, so the two do not fight over the cursor. Defaults
            to a fresh console.
        width: Width of the rendered image, either a number of terminal cells or a
            percentage of the console width such as ``"100%"``.
        match_background: Whether to ask the terminal for its background color and
            style the figures to match it.

    Yields:
        A pyplot-compatible object whose ``show`` renders to the console.
    """
    console = Console() if console is None else console
    background = terminal_background() if match_background else None

    # Recorded before the body runs, so figures the caller already had open are
    # neither rendered nor closed by this block.
    proxy = _RichPyplot(console, set(plt.get_fignums()), width)

    # The styling has to stay active while figures are *created* and while they are
    # saved to PNG, which is why show() happens inside the block rather than after it.
    with _terminal_style(background):
        yield proxy

        # Skipped when the body raises: a half-drawn figure is not worth printing.
        proxy.show()
