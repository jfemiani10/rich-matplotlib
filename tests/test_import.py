"""Smoke test: the package imports and reports a version."""

import rich_matplotlib


def test_package_has_version():
    assert isinstance(rich_matplotlib.__version__, str)
    assert rich_matplotlib.__version__
