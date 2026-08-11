"""Shared pytest configuration.

Matplotlib must be told to use the non-interactive "Agg" backend before ``pyplot`` is
imported anywhere, otherwise it tries to open a GUI window on machines that have one
and fails on machines that do not. Conftest runs before any test module is imported,
which makes it the right place for this.
"""

import matplotlib
import pytest

matplotlib.use("Agg")


@pytest.fixture(autouse=True)
def close_figures():
    """Close every figure after each test so leftovers cannot leak between tests."""
    yield

    import matplotlib.pyplot as plt

    plt.close("all")
