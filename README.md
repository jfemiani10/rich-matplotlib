# rich-matplotlib

[![CI](https://github.com/jfemiani10/rich-matplotlib/actions/workflows/ci.yml/badge.svg)](https://github.com/jfemiani10/rich-matplotlib/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green)](https://github.com/jfemiani10/rich-matplotlib/blob/main/LICENSE)

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

Because the figure is printed *through* a rich `Console` rather than written straight to
stdout, it composes with the rest of a rich terminal UI: a progress bar can stay pinned
at the bottom of the screen while plots scroll past above it, and a `Live` display can
animate a figure in place. See [Related projects](#related-projects) for how that differs
from the backend-based approach.

![Two sine waves plotted as a sixel image inside a terminal, with ordinary text above and below it](https://raw.githubusercontent.com/jfemiani10/rich-matplotlib/main/doc/demos_basic_plot.png)

## Install

```bash
pip install rich-matplotlib
```

Requires Python 3.10 or newer. For the unreleased version:

```bash
pip install git+https://github.com/jfemiani10/rich-matplotlib.git
```

## Terminal setup

Read this part before deciding the library is broken.

The renderer is chosen once, when the package is imported, by asking your terminal what
it can do. Everything degrades rather than failing:

| Terminal | Result |
| --- | --- |
| foot, WezTerm, Konsole, mlterm, Windows Terminal, xterm with sixel | Sixel image |
| Kitty, Ghostty | Kitty graphics protocol |
| VS Code's integrated terminal | Sixel image, *once images are enabled* — see below |
| Anything else with 24-bit color | Colored half-blocks |
| Piped to a file, CI, no color | Plain unicode blocks |

### VS Code

VS Code's integrated terminal can show images, but not until you turn it on. Search the
settings for `enableImages` and tick **Terminal › Integrated: Enable Images**:

![The VS Code settings editor filtered to "enableImages", showing the Terminal > Integrated: Enable Images checkbox ticked](https://raw.githubusercontent.com/jfemiani10/rich-matplotlib/main/doc/settings_enable_images.png)

Two conditions come with it:

- **Terminal › Integrated: Gpu Acceleration** must be enabled — images do not work in the
  DOM renderer.
- On **Windows**, image protocols need ConPTY v2 or newer, which means enabling
  **Terminal › Integrated: Windows Use Conpty Dll**.

Without this, plots still appear — as colored half-blocks — so a blocky figure in VS Code
usually means the setting rather than a bug.

### If the figure looks garbled or overlaps your text

Rendering goes through [textual-image](https://github.com/lnqs/textual-image), which
places an image by reserving the terminal rows it needs. If the image is taller than the
terminal itself there are not enough rows to reserve, and it smears into the surrounding
text.

The fix is one of:

- make the terminal window taller,
- reduce the figure height (`richplot(height=20)`, or a shorter `figsize`),
- or use `width="auto"`, which caps the height at the console height for you.

See [Sizing](#sizing) for the details.

## Related projects

The usual way to get matplotlib into a terminal is a **backend**:
[matplotlib-backend-sixel](https://github.com/koppa/matplotlib-backend-sixel) and
[itermplot](https://github.com/daleroberts/itermplot) both work this way. You select the
backend once, and from then on every `plt.show()` writes an image to stdout:

```python
import matplotlib

matplotlib.use("module://matplotlib-backend-sixel")

import matplotlib.pyplot as plt

plt.plot([1, 2, 3])
plt.show()  # goes to the terminal
```

That is a genuinely nice property: existing scripts need no changes at all. The trade-off
is that it is a global, all-or-nothing switch, and the image is written directly to
stdout, behind the back of anything else drawing on the screen.

`rich_matplotlib` is scoped instead of global, and it prints through a rich `Console`:

| | Backend (`matplotlib-backend-sixel`, `itermplot`) | `rich_matplotlib` |
| --- | --- | --- |
| How you opt in | Global — `matplotlib.use(...)` for the whole process | Per block — `with richplot() as plt:` |
| Output path | Escape codes written straight to stdout | Printed through a rich `Console` |
| Alongside a rich progress bar or `Live` panel | Fights it for the cursor; output gets overwritten | Rich sequences the two; the bar stays put |
| Non-terminal output (pipe, CI) | Sixel codes into your logs | Degrades to unicode blocks |
| Rest of the program | Also redirected | Untouched — GUI or `savefig` still work |

The last row is the practical one. Because `richplot` only touches figures created inside
its block, a script can render a quick check to the terminal and still write its real
output to a file, with no backend juggling.

**The composition point is worth spelling out.** A rich `Progress` bar or `Live` display
owns the bottom of the screen and redraws it continuously. Anything that writes to stdout
without telling rich gets overwritten or shredded — which is what happens when a sixel
backend and a progress bar share a terminal. Handing `richplot` the *same* console lets
rich order the writes, so plots scroll up above a progress bar that never moves:

```python
with Progress(console=console) as progress:
    for chunk in chunks:
        ...
        with richplot(console=console) as plt:  # prints above the bar
            plt.plot(chunk)
        progress.advance(task)
```

Two neighbours worth knowing about, which do not involve matplotlib at all:
[plotext](https://github.com/piccolomo/plotext) draws plots out of unicode characters
with its own API, and [textual-image](https://github.com/lnqs/textual-image) is the image
protocol layer this library renders through.

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

For an animation, `figure_image()` gives you the figure as a rich renderable instead of
printing it, which is what `Live` needs to redraw a plot in place:

```python
from rich.live import Live
from rich_matplotlib import figure_image, terminal_background, terminal_style

# richplot styles figures for you; a hand-built figure has to opt in, and the styling
# must be active while the figure is *created*.
with terminal_style(terminal_background()):
    figure, line = build_figure()

    with Live(console=console, auto_refresh=False) as live:
        for phase in phases:
            line.set_ydata(np.sin(x + phase))
            live.update(figure_image(figure, width="70%"), refresh=True)
```

Reuse one figure and replace its data, rather than building a figure per frame: it is
faster, and it stops matplotlib rescaling the axes so the image twitches between frames.
`figure_image` never closes anything, so closing is yours to do. See
[`demos/live_plot.py`](https://github.com/jfemiani10/rich-matplotlib/blob/main/demos/live_plot.py).

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

### Centering, and other print options

A figure narrower than the console sits against the left margin by default. `justify`
moves it:

```python
with richplot(width="70%", justify="center") as plt:
    ...
```

`justify` is not special-cased — any keyword `richplot` does not recognize is handed
straight to `console.print`, so `justify="right"`, `style=...` and the rest of rich's
print options work the same way. They apply to every figure the block renders.

Centering only shows up when there is space to center *in*. At the default
`width="100%"` the image already fills the console, so `justify` has nothing to do.

Building the renderable yourself with `figure_image()` skips this, since nothing is
being printed — pass `justify` to your own `console.print` instead.

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
| `richplot(console=None, width="100%", height="auto", match_background=True, **print_options)` | Context manager yielding a `pyplot` stand-in. Extra keywords (`justify="center"`, …) go to `console.print`. |
| `figure_image(figure, width="100%", height="auto")` | One figure as a rich renderable, for `Live` or any other rich layout. Does not print or close it. |
| `terminal_background(timeout=1.0)` | The terminal's background as `(r, g, b)` in 0-255, or `None` if it cannot be determined. |
| `terminal_style(color)` | Context manager styling matplotlib to blend into that background. Applied by `richplot`; needed by hand only alongside `figure_image`. |

## Demos

Runnable examples in
[`demos/`](https://github.com/jfemiani10/rich-matplotlib/tree/main/demos), which ship in
the sdist but not the wheel — clone the repo to run them:

```bash
python demos/basic_plot.py           # one figure, the smallest possible example
python demos/multiple_figures.py     # render order, and rendering mid-block
python demos/rich_composition.py     # plots scrolling above a pinned progress bar
python demos/live_plot.py            # a sine wave animated in place with rich Live
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
