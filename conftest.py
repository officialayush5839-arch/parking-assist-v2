"""Root-level conftest.

Guarantees the project root is importable under pytest on all platforms
(Windows included).  Without this, ``tests/conftest.py`` and the test
modules fail to import ``app``, ``core``, ``simulation`` etc. when the
root directory is not already on ``sys.path``.
"""

from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)