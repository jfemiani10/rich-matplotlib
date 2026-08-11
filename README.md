# rich-matplotlib

[![CI](https://github.com/jfemiani10/rich-matplotlib/actions/workflows/ci.yml/badge.svg)](https://github.com/jfemiani10/rich-matplotlib/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Display matplotlib figures directly in your terminal, as real images, using
[rich](https://github.com/Textualize/rich) and sixel graphics.

No GUI window, no saving PNGs to look at later, no notebook. Plot over SSH, plot from a
tmux pane, plot in the middle of a long-running script — the figure appears inline with
the rest of your output.

```python
from rich_matplotlib import richplot

with richplot() as plt:
    plt.plot([1, 2, 3], [4, 5, 6])
    plt.title("Hello from the terminal")
```

Inside the block, `plt` behaves like `matplotlib.pyplot`. Any figure still open when the
block ends is rendered automatically, so there is nothing new to remember.

## Install

Not on PyPI yet, so install from the repository:

```bash
pip install git+https://github.com/jfemiani10/rich-matplotlib.git
```

Requires Python 3.10 or newer.

## Terminal support

The renderer is chosen once, when the package is imported, by asking your terminal what
it can do. Everything degrades rather than failing:

| Terminal | Result |
| --- | --- |
| foot, WezTerm, Konsole, mlterm, Windows Terminal, xterm with sixel | Sixel image |
| Kitty, Ghostty | Kitty graphics protocol |
| Anything else with 24-bit color | Colored half-blocks |
| Piped to a file, CI, no color | Plain unicode blocks |

VS Code's integrated terminal has no graphics protocol, so expect blocks there.

## Usage

### Matching your terminal's background

By default the library asks the terminal for its background color (via an OSC 11 escape
sequence) and paints the figure to match, so plots blend into the surrounding text
instead of sitting in a white rectangle. Dark terminals also get matplotlib's
`dark_background` style so the ink stays readable.

```python
with richplot(match_background=False) as plt:  # keep matplotlib's white canvas
    ...
```

Terminals that ignore the query, and non-terminals such as CI, simply keep matplotlib's
default styling.

### Composing with rich

Pass your own `Console` so a live display and a plot do not fight over the cursor:

```python
from rich.console import Console
from rich.progress import Progress
from rich_matplotlib import richplot

console = Console()

with Progress(console=console) as progress:
    ...  # long-running work

with richplot(console=console) as plt:
    plt.plot(results)
```

### Sizing

By default figures fill the console's width, and take whatever height keeps their
proportions intact.

`width` and `height` each accept a number of terminal cells, a percentage of the
console, or `"auto"`:

```python
with richplot(width="60%") as plt:  # default is width="100%", height="auto"
    ...
```

`height="auto"` derives the height from the width, which is what keeps the figure's
aspect ratio intact — so setting `width` alone is usually all you want.

The one consequence to know: a tall figure at full width can end up taller than the
screen and scroll. `width="auto"` gives up some width to keep the whole plot visible
at once:

```python
with richplot(width="auto") as plt:  # never taller than the console
    ...
```

Sizing both axes explicitly resizes the figure into exactly that box with no regard for
its shape, which is only what you want if the figure already matches it.

Wide, short figures suit a terminal better than matplotlib's default shape, so
`plt.figure(figsize=(8, 4))` is worth setting — tall enough to keep an `xlabel` from
being clipped, and wide enough that it does not tower over the rest of your output.

### Rendering early

`show()` renders and closes every figure created so far, exactly like `plt.show()`.
Pass `close=False` to keep the figures open and add to them later:

```python
with richplot() as plt:
    plt.plot(first_batch)
    plt.show(close=False)  # rendered now, figure stays open
    plt.plot(second_batch)  # same figure, rendered again on exit
```

## API

| Object | Description |
| --- | --- |
| `richplot(console=None, width="100%", height="auto", match_background=True)` | Context manager yielding a `pyplot` stand-in. |
| `terminal_background(timeout=1.0)` | The terminal's background as `(r, g, b)` in 0-255, or `None` if it cannot be determined. |

## Demos

Runnable examples in [`demos/`](demos/):

```bash
python demos/basic_plot.py           # one figure, the smallest possible example
python demos/multiple_figures.py     # render order, and rendering mid-block
python demos/rich_composition.py     # a progress bar, a table and a plot on one console
python demos/background_matching.py  # the same figure with and without blending
```

## Development

```bash
git clone https://github.com/jfemiani10/rich-matplotlib.git
cd rich-matplotlib
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Lint and format on commit, run the tests on push
pre-commit install --hook-type pre-commit --hook-type pre-push
```

Then:

```bash
pytest              # tests
ruff check .        # lint
ruff format .       # format
```

CI runs the same checks on Python 3.10 through 3.13.

## How it works

1. `richplot()` yields a proxy object that forwards every attribute to
   `matplotlib.pyplot` except `show`.
2. On exit, each figure created inside the block is saved to an in-memory PNG.
3. [textual-image](https://github.com/lnqs/textual-image) converts the PNG into whatever
   your terminal understands, and rich prints it.

Only figures created inside the block are touched; anything you already had open is left
alone.

## License

MIT
