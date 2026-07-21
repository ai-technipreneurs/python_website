"""Sync PyPro-SCiDaS source notebooks into python_website/notebooks/.

Copies the 18 source lecture notebooks (+ index) from the local class folder
into the repo. Internal hrefs that point at sibling source notebooks are
rewritten to absolute deployed-site URLs (`.html` on GitHub Pages), so that
prev / next / index navigation works when the site serves the built HTML —
GitHub Pages doesn't serve raw `.ipynb`, so relative `.ipynb` hrefs 404.

Colab opens the raw `.ipynb` off the repo, so the internal links there
route the reader to the site rather than to another Colab tab. That's the
intended trade-off; the source notebooks kept in the class folder retain
their relative `.ipynb` navigation for local Jupyter use.

Run from anywhere; paths are resolved relative to this file.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = REPO_ROOT.parent / "notebooks-python-class-2025"
DEST_DIR = REPO_ROOT / "notebooks"

# Image files are ALSO mirrored to a separate asset directory so Sphinx's
# `html_extra_path` can copy them into the built site under notebooks/*.
# The mirror is required because Sphinx doesn't auto-copy images referenced
# from raw HTML `<img>` tags (only from markdown ![](...) form), and we
# can't point `html_extra_path` at `notebooks/` itself — Sphinx would then
# exclude the notebooks from the docs build.
IMAGE_MIRROR_DIR = REPO_ROOT / "notebook-assets" / "notebooks"

# Notebook JSON stores HTML with escaped quotes, so an `<img src="foo.png">`
# ends up as `<img src=\"foo.png\">` in the raw file text. Match either
# an escaped-quote pair (`src=\"...\"`) or a plain quote (`src="..."`),
# plus the Markdown image form `![alt](foo.png)`.
IMG_REF_RE = re.compile(
    r'src=\\?["\']([^"\'\\\s>]+\.(?:png|jpg|jpeg|gif|svg))\\?["\']'
    r'|!\[[^\]]*\]\(([^)]+\.(?:png|jpg|jpeg|gif|svg))\)',
    re.IGNORECASE,
)

SITE_BASE = "https://ai-technipreneurs.github.io/python_website/notebooks/"

FILENAME_MAP: dict[str, str] = {
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


def _url_for(dest_name: str) -> str:
    """Return the absolute deployed-site URL for a destination ipynb name."""
    return SITE_BASE + dest_name[: -len(".ipynb")] + ".html"


def rewrite(text: str) -> str:
    """Replace every reference to a source ipynb with the deployed-site URL.

    Longest keys first so `PyPro-SCiDaS-lec_10_numpy_part1.ipynb` never gets
    partial-matched by a shorter substring.
    """
    for src_name, dst_name in sorted(FILENAME_MAP.items(), key=lambda kv: -len(kv[0])):
        text = text.replace(src_name, _url_for(dst_name))
    return text


def collect_image_refs(text: str) -> set[str]:
    """Return every relative image reference (basename or subpath, no scheme)."""
    refs: set[str] = set()
    for m in IMG_REF_RE.finditer(text):
        ref = (m.group(1) or m.group(2) or "").replace("\\/", "/")
        # Skip absolute URLs and Jupyter attachments (embedded base64 in notebook JSON).
        if not ref or ref.startswith(("http:", "https:", "attachment:", "data:", "/")):
            continue
        refs.add(ref)
    return refs


def main() -> None:
    if not SOURCE_DIR.is_dir():
        raise SystemExit(f"Source folder missing: {SOURCE_DIR}")
    DEST_DIR.mkdir(parents=True, exist_ok=True)

    missing: list[str] = []
    written: list[tuple[str, str, int]] = []
    all_img_refs: set[str] = set()
    for src_name, dst_name in FILENAME_MAP.items():
        src_path = SOURCE_DIR / src_name
        if not src_path.is_file():
            missing.append(src_name)
            continue
        content = src_path.read_text(encoding="utf-8")
        all_img_refs.update(collect_image_refs(content))
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

    # Copy every referenced image file to two locations:
    #   1. Alongside the destination notebooks under notebooks/  — needed
    #      by Colab (which reads raw ipynb + sibling images from GitHub).
    #   2. Into notebook-assets/notebooks/  — Sphinx's html_extra_path
    #      copies this tree verbatim to _build/html/notebooks/*, which is
    #      how the images end up served on the deployed site.
    print(f"\nSyncing {len(all_img_refs)} referenced image(s):")
    IMAGE_MIRROR_DIR.mkdir(parents=True, exist_ok=True)
    img_missing: list[str] = []
    for ref in sorted(all_img_refs):
        src_img = SOURCE_DIR / ref
        if not src_img.is_file():
            img_missing.append(ref)
            print(f"  MISSING: {ref}")
            continue
        for dst_dir in (DEST_DIR, IMAGE_MIRROR_DIR):
            dst_img = dst_dir / ref
            dst_img.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_img, dst_img)
        print(f"  {ref}  ({src_img.stat().st_size:,} bytes) -> notebooks/ + notebook-assets/notebooks/")
    if img_missing:
        print(f"\n{len(img_missing)} referenced image(s) not found in source folder.")


if __name__ == "__main__":
    main()
