"""Tests for parsing the terminal's OSC 11 background-color reply."""

import io

import pytest

from rich_matplotlib import _core
from rich_matplotlib._core import _parse_osc11_reply, _scale_to_byte, terminal_background


@pytest.mark.parametrize(
    ("component", "expected"),
    [
        ("0", 0),
        ("f", 255),
        ("00", 0),
        ("ff", 255),
        ("80", 128),
        ("0000", 0),
        ("ffff", 255),
        ("1e1e", 30),
    ],
)
def test_scale_to_byte_handles_any_component_width(component, expected):
    assert _scale_to_byte(component) == expected


@pytest.mark.parametrize(
    ("sequence", "expected"),
    [
        ("\x1b]11;rgb:0000/0000/0000\x1b\\", (0, 0, 0)),
        ("\x1b]11;rgb:ffff/ffff/ffff\x1b\\", (255, 255, 255)),
        ("\x1b]11;rgb:1e1e/1e1e/1e1e\x1b\\", (30, 30, 30)),
        ("\x1b]11;rgb:ff/00/00\x1b\\", (255, 0, 0)),
        ("\x1b]11;rgb:FFFF/0000/0000\x1b\\", (255, 0, 0)),
    ],
)
def test_parse_osc11_reply_accepts_valid_replies(sequence, expected):
    assert _parse_osc11_reply(sequence) == expected


@pytest.mark.parametrize(
    "sequence",
    [
        "",
        "not an escape sequence",
        "\x1b]11;rgb:0000/0000\x1b\\",  # only two channels
        "\x1b]11;#1e1e1e\x1b\\",  # legacy '#rrggbb' form, not supported
        "\x1b]11;rgb:zzzz/0000/0000\x1b\\",  # not hex
        "\x1b]11;rgb:0000/0000/0000",  # missing string terminator
    ],
)
def test_parse_osc11_reply_rejects_malformed_replies(sequence):
    assert _parse_osc11_reply(sequence) is None


def test_terminal_background_returns_none_without_a_tty(monkeypatch):
    """Piped output and CI runners have no terminal to query; that must not raise."""
    monkeypatch.setattr(_core.sys, "__stdin__", io.StringIO())
    monkeypatch.setattr(_core.sys, "__stdout__", io.StringIO())

    assert terminal_background(timeout=0.01) is None


def test_terminal_background_returns_none_when_streams_are_closed(monkeypatch):
    """Detached processes can have stdin/stdout set to None entirely."""
    monkeypatch.setattr(_core.sys, "__stdin__", None)
    monkeypatch.setattr(_core.sys, "__stdout__", None)

    assert terminal_background(timeout=0.01) is None
