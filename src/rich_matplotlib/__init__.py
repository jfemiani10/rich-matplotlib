"""Display matplotlib figures directly in the terminal using rich and sixel graphics.

    >>> from rich_matplotlib import richplot
    >>> with richplot() as plt:  # doctest: +SKIP
    ...     plt.plot([1, 2, 3], [4, 5, 6])

The implementation lives in the private ``_core`` module; everything meant for public
use is re-exported here, so the import path stays stable if that module is ever split.
"""

from ._core import figure_image, richplot, terminal_background, terminal_style

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "figure_image",
    "richplot",
    "terminal_background",
    "terminal_style",
]
