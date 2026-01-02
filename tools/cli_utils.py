import os
import sys

def enable_ansi_support():
    """
    Enables ANSI escape sequence support on Windows using colorama.
    On non-Windows platforms, this is a no-op.
    """
    if sys.platform.startswith("win"):
        try:
            import colorama
            colorama.init()
        except ImportError:
            pass  # colorama not installed, ANSI codes might not work
