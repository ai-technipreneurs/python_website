"""Sync PyPro-SCiDaS source notebooks into python_website/notebooks/.

Copies the 18 source lecture notebooks (+ index) from the local class folder
into the repo, rewriting every internal href from the long PyPro-SCiDaS-*
filenames to the short NN-shortname.ipynb names used in the site's _toc.yml.

Run from anywhere; paths are resolved relative to this file.
"""

from __future__ import annotations

import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = REPO_ROOT.parent / "notebooks-python-class-2025"
DEST_DIR = REPO_ROOT / "notebooks"

MAPPING: dict[str, str] = {
    "PyPro-SCiDaS-index.ipynb": "index.ipynb",
    "PyPro-SCiDaS-lec_00_introduction_to_shell.ipynb": "00-shell.ipynb",
    "PyPro-SCiDaS-lec_01_introduction_to_python.ipynb": "01-intro-python.ipynb",
    "PyPro-SCiDaS-lec_02_variables_types_and_assignment.ipynb": "02-variables.ipynb",
    "PyPro-SCiDaS-lec_03_strings_and_files.ipynb": "03-strings-files.ipynb",
    "PyPro-SCiDaS-lec_04_version_control_with_git.ipynb": "04-git.ipynb",
    "PyPro-SCiDaS-lec_05_iterable_objects_or_containers.ipynb": "05-containers.ipynb",
    "PyPro-SCiDaS-lec_06_flow_control_and_loops.ipynb": "06-flow-control.ipynb",
    "PyPro-SCiDaS-lec_07_functions_modules_and_packages.ipynb": "07-functions.ipynb",
    "PyPro-SCiDaS-lec_08_recursion_and_lambda.ipynb": "08-recursion-lambda.ipynb",
    "PyPro-SCiDaS-lec_09_errors_and_debugging.ipynb": "09-errors-debugging.ipynb",
    "PyPro-SCiDaS-lec_10_numpy_part1.ipynb": "10-numpy-1.ipynb",
    "PyPro-SCiDaS-lec_11_numpy_part2.ipynb": "11-numpy-2.ipynb",
    "PyPro-SCiDaS-lec_12_matplotlib.ipynb": "12-matplotlib.ipynb",
    "PyPro-SCiDaS-lec_13_object_oriented_programming.ipynb": "13-oop.ipynb",
    "PyPro-SCiDaS-lec_14_list_comprehensions_and_generators.ipynb": "14-comprehensions.ipynb",
    "PyPro-SCiDaS-lec_15_pandas_for_data_analysis.ipynb": "15-pandas.ipynb",
    "PyPro-SCiDaS-lec_16_decorators_and_context_managers.ipynb": "16-decorators.ipynb",
    "PyPro-SCiDaS-lec_17_data_formats_and_apis.ipynb": "17-data-apis.ipynb",
}


def rewrite(text: str) -> str:
    # Longer source names first so index doesn't shadow a lec_* match.
    for src, dst in sorted(MAPPING.items(), key=lambda kv: -len(kv[0])):
        text = text.replace(src, dst)
    return text


def main() -> None:
    if not SOURCE_DIR.is_dir():
        raise SystemExit(f"Source folder missing: {SOURCE_DIR}")
    DEST_DIR.mkdir(parents=True, exist_ok=True)

    missing: list[str] = []
    written: list[tuple[str, str, int]] = []
    for src_name, dst_name in MAPPING.items():
        src_path = SOURCE_DIR / src_name
        if not src_path.is_file():
            missing.append(src_name)
            continue
        content = src_path.read_text(encoding="utf-8")
        rewritten = rewrite(content)
        dst_path = DEST_DIR / dst_name
        dst_path.write_text(rewritten, encoding="utf-8", newline="\n")
        delta = len(rewritten) - len(content)
        written.append((src_name, dst_name, delta))

    print(f"Wrote {len(written)} notebooks to {DEST_DIR}")
    for src, dst, delta in written:
        print(f"  {src}  ->  {dst}  ({delta:+d} bytes)")
    if missing:
        print(f"\nMissing sources ({len(missing)}):")
        for m in missing:
            print(f"  - {m}")


if __name__ == "__main__":
    main()
