import os
import sys
import importlib
from collections import namedtuple
from unittest.mock import patch, PropertyMock

import pytest

import src.aniworld.menu as menu

VersionInfo = namedtuple("VersionInfo", ["major", "minor"])
MOCK_VERSION = VersionInfo(3, 14)


def test_patched_max_physical_fallback():
    """
    Test that _patched_max_physical correctly falls back to (23, 79)
    when curses throws an Exception and os.get_terminal_size() throws an OSError.
    """
    try:
        # 1. Patch sys.version_info and reload to ensure the function is defined
        with patch("sys.version_info", MOCK_VERSION):
            importlib.reload(menu)

            # 2. Patch curses to throw an Exception
            with patch("src.aniworld.menu.curses") as mock_curses:
                # We want curses.LINES or curses.COLS access to raise an Exception
                # Rather than patching type(mock_curses), which is MagicMock globally, we'll patch the instance __sub__ method to raise Exception on subtract
                mock_curses.LINES.__sub__.side_effect = Exception("Mocked curses error")

                # 3. Patch os.get_terminal_size to throw OSError
                with patch("os.get_terminal_size", side_effect=OSError("Mocked OSError")):

                    # Check that the function exists
                    assert hasattr(menu, "_patched_max_physical"), "_patched_max_physical should be defined for Python 3.14+"

                    # Call the function (pass None as 'self' parameter)
                    result = menu._patched_max_physical(None)

                    # Verify it returned the fallback value: size.lines - 1, size.columns - 1
                    # os.terminal_size((80, 24)) gives lines=24, columns=80, so (23, 79)
                    assert result == (23, 79)
    finally:
        # Clean up by reloading without the patch so we don't break other tests
        importlib.reload(menu)
