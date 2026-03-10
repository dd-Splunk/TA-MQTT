"""
TA-MQTT  —  sys.path bootstrap
================================
This module is imported at the very top of every entry-point script.
It ensures that the add-on's ``lib/`` directory is first on sys.path so
that bundled dependencies (paho-mqtt, splunktaucclib, etc.) take precedence
over anything else installed on the system.

Generated / maintained by ``ucc-gen build`` — do not edit manually.
"""

import os
import sys

# Resolve the absolute path to the add-on root (TA-MQTT/)
_ta_dir = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

# Paths to inject (in priority order, highest first)
_extra_paths = [
    os.path.join(_ta_dir, "lib"),
    os.path.join(_ta_dir, "bin"),
]

for _p in reversed(_extra_paths):
    if _p not in sys.path:
        sys.path.insert(0, _p)
