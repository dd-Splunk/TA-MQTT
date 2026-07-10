"""
TA-MQTT  —  additional_packaging.py
=====================================
Post-build hook executed by ``ucc-gen build``.

- Removes bytecode artifacts that AppInspect rejects.
- Patches UCC monitoring dashboard definitions (single global time token,
  remove duplicate time-range labels, 60s auto-refresh).

Reference: https://splunk.github.io/addonfactory-ucc-generator/additional_packaging/
"""

from __future__ import annotations

import glob
import json
import os
import shutil
from typing import Any

GLOBAL_TIME_TOKEN = "global_time"
GLOBAL_TIME_DEFAULT = "-24h,now"

LEGACY_TIME_TOKENS = (
    "overview_time",
    "data_ingestion_time",
    "errors_tab_time",
    "resource_tab_time",
    "data_ingestion_modal_time",
)

TAB_TIMERANGE_INPUTS = (
    "data_ingestion_input",
    "errors_tab_input",
    "resource_tab_input",
    "data_ingestion_modal_input",
)

REFRESH_DEFAULTS: dict[str, Any] = {
    "dataSources": {
        "ds.search": {
            "options": {
                "refresh": {
                    "type": "delay",
                    "value": 60,
                }
            }
        },
        "ds.chain": {
            "options": {
                "refresh": {
                    "type": "delay",
                    "value": 60,
                }
            }
        },
    },
}

DASHBOARD_DEFINITION_FILES = (
    "overview_definition.json",
    "data_ingestion_tab_definition.json",
    "errors_tab_definition.json",
    "resources_tab_definition.json",
    "data_ingestion_modal_definition.json",
)


def additional_packaging(ta_name: str | None = None) -> None:
    """Patch UCC monitoring dashboard assets after the build output is ready."""
    name = ta_name or "TA-MQTT"
    output_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", name)
    if not os.path.isdir(output_root):
        return

    patched_defs = patch_dashboard_definitions(output_root)
    patched_styles = patch_dashboard_page_styles(output_root)
    print(
        "[additional_packaging] Dashboard patch complete "
        f"patched_dashboard_definitions={patched_defs} patched_dashboard_styles={patched_styles}"
    )


def cleanup_output_files(output_path: str, ta_name: str) -> None:
    """Remove bytecode artifacts that AppInspect rejects from build output."""
    output_root = os.path.join(output_path, ta_name)
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


def patch_dashboard_definitions(output_root: str) -> int:
    """Normalize generated UCC dashboard JSON definitions."""
    custom_dir = os.path.join(
        output_root, "appserver", "static", "js", "build", "custom"
    )
    if not os.path.isdir(custom_dir):
        return 0

    patched = 0
    for filename in DASHBOARD_DEFINITION_FILES:
        path = os.path.join(custom_dir, filename)
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8") as handle:
            definition = json.load(handle)
        if _patch_definition_object(definition, filename):
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(definition, handle, indent=2)
                handle.write("\n")
            patched += 1
    return patched


HIDE_TAB_TIMERANGE_CSS = """
    [data-input-id='data_ingestion_input'],
    [data-input-id='errors_tab_input'],
    [data-input-id='resource_tab_input'],
    [data-input-id='data_ingestion_modal_input'] {
        display: none !important;
    }
"""


def patch_dashboard_page_styles(output_root: str) -> int:
    """Hide any tab-level timerange inputs; Overview keeps the only visible picker."""
    build_dir = os.path.join(output_root, "appserver", "static", "js", "build")
    if not os.path.isdir(build_dir):
        return 0

    patched = 0
    marker = "/* ta-mqtt-single-global-time */"
    for path in glob.glob(os.path.join(build_dir, "Dashboard.DashboardPage.*.js")):
        with open(path, encoding="utf-8") as handle:
            content = handle.read()
        if marker in content:
            continue
        if "[data-input-id='overview_input']" not in content:
            continue
        updated = content.replace(
            "[data-input-id='overview_input'] {",
            f"{marker}\n    {HIDE_TAB_TIMERANGE_CSS.strip()}\n\n    [data-input-id='overview_input'] {{",
            1,
        )
        if updated != content:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(updated)
            patched += 1
    return patched


def _patch_definition_object(definition: dict[str, Any], filename: str) -> bool:
    changed = False

    serialized = json.dumps(definition)
    updated = serialized
    for legacy_token in LEGACY_TIME_TOKENS:
        if legacy_token == GLOBAL_TIME_TOKEN:
            continue
        updated = updated.replace(f"${legacy_token}.", f"${GLOBAL_TIME_TOKEN}.")
        updated = updated.replace(
            f'"token": "{legacy_token}"',
            f'"token": "{GLOBAL_TIME_TOKEN}"',
        )
    if updated != serialized:
        definition.clear()
        definition.update(json.loads(updated))
        changed = True

    visualizations = definition.get("visualizations", {})
    for viz_name in list(visualizations):
        if "timerange_label" in viz_name:
            if visualizations.pop(viz_name, None) is not None:
                changed = True

    data_sources = definition.get("dataSources", {})
    for ds_name in list(data_sources):
        if any(
            suffix in ds_name for suffix in ("_time_label_start_ds", "_time_label_end_ds")
        ):
            data_sources.pop(ds_name, None)
            changed = True

    inputs = definition.get("inputs", {})
    for input_name in TAB_TIMERANGE_INPUTS:
        if inputs.pop(input_name, None) is not None:
            changed = True

    layout = definition.get("layout", {})
    global_inputs = layout.get("globalInputs", [])
    if global_inputs:
        filtered = [item for item in global_inputs if item not in TAB_TIMERANGE_INPUTS]
        if filtered != global_inputs:
            layout["globalInputs"] = filtered
            changed = True

    structure = layout.get("structure", [])
    if structure:
        filtered_structure = [
            item
            for item in structure
            if "timerange_label" not in str(item.get("item", ""))
        ]
        if filtered_structure != structure:
            layout["structure"] = filtered_structure
            changed = True

    if filename == "overview_definition.json":
        overview_input = inputs.get("overview_input")
        if overview_input and overview_input.get("type") == "input.timerange":
            options = overview_input.setdefault("options", {})
            if options.get("token") != GLOBAL_TIME_TOKEN:
                options["token"] = GLOBAL_TIME_TOKEN
                changed = True
            if options.get("defaultValue") != GLOBAL_TIME_DEFAULT:
                options["defaultValue"] = GLOBAL_TIME_DEFAULT
                changed = True
    elif filename != "overview_definition.json":
        # Tab/modal definitions keep $global_time$ references only (no local picker).
        global_inputs = layout.get("globalInputs", [])
        filtered_global = [
            item
            for item in global_inputs
            if item not in TAB_TIMERANGE_INPUTS and item != "overview_input"
        ]
        if filtered_global != global_inputs:
            layout["globalInputs"] = filtered_global
            changed = True

    defaults = definition.setdefault("defaults", {})
    merged_defaults = json.loads(json.dumps(REFRESH_DEFAULTS))
    if defaults.get("dataSources") != merged_defaults.get("dataSources"):
        definition["defaults"] = merged_defaults
        changed = True

    return changed
