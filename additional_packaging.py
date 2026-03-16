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
import shutil


def additional_packaging(ta_name: str) -> None:
    lib_dir = os.path.join("output", ta_name, "lib")
    req_file = os.path.join("package", "lib", "requirements.txt")

    if not os.path.isfile(req_file):
        print(
            f"[additional_packaging] No requirements.txt found at {req_file}, skipping."
        )
        return

    print(f"[additional_packaging] Installing Python dependencies into {lib_dir} …")
    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-r",
            req_file,
            "--target",
            lib_dir,
            "--no-deps",  # avoid pulling in transitive deps that conflict with Splunk
            "--upgrade",
        ]
    )
    print("[additional_packaging] Done.")


def cleanup_output_files(output_directory: str, ta_name: str) -> None:
    output_root = os.path.join(output_directory, ta_name)
    if not os.path.isdir(output_root):
        return

    removed_dirs = 0
    removed_files = 0

    for root, dirs, files in os.walk(output_root, topdown=True):
        for dirname in list(dirs):
            if dirname == "__pycache__":
                path = os.path.join(root, dirname)
                shutil.rmtree(path, ignore_errors=True)
                dirs.remove(dirname)
                removed_dirs += 1

        for filename in files:
            if filename.endswith((".pyc", ".pyo")):
                path = os.path.join(root, filename)
                try:
                    os.remove(path)
                    removed_files += 1
                except OSError:
                    pass

    print(
        "[additional_packaging] Cleanup complete "
        f"removed_pycache_dirs={removed_dirs} removed_bytecode_files={removed_files}"
    )
