"""
TA-MQTT  —  additional_packaging.py
=====================================
Optional post-build hook executed by ``ucc-gen build``.

If ``package/lib/requirements.txt`` is not picked up automatically by your
version of ucc-gen, this script installs the Python dependencies manually
into the generated ``lib/`` directory.

Reference: https://splunk.github.io/addonfactory-ucc-generator/additional_packaging/
"""

import subprocess
import sys
import os


def additional_packaging(ta_name: str) -> None:
    lib_dir = os.path.join("output", ta_name, "lib")
    req_file = os.path.join("package", "lib", "requirements.txt")

    if not os.path.isfile(req_file):
        print(f"[additional_packaging] No requirements.txt found at {req_file}, skipping.")
        return

    print(f"[additional_packaging] Installing Python dependencies into {lib_dir} …")
    subprocess.check_call(
        [
            sys.executable, "-m", "pip", "install",
            "-r", req_file,
            "--target", lib_dir,
            "--no-deps",            # avoid pulling in transitive deps that conflict with Splunk
            "--upgrade",
        ]
    )
    print("[additional_packaging] Done.")
