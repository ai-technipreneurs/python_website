"""Extract every http(s) URL from all notebooks, check each once,
report status (200 / redirect / 4xx / 5xx / connection error).
"""

from __future__ import annotations

import json
import re
import concurrent.futures
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parent.parent / "notebooks"

URL_RE = re.compile(r"https?://[^\s\"'<>\)\]\\]+")
UA = "Mozilla/5.0 (audit)"

def check(url: str) -> tuple[str, str]:
    try:
        r = Request(url, headers={"User-Agent": UA}, method="HEAD")
        with urlopen(r, timeout=10) as resp:
            return url, f"{resp.status} {resp.reason or ''}".strip()
    except HTTPError as e:
        # Some servers reject HEAD but accept GET
        if e.code in (403, 405, 501):
            try:
                r = Request(url, headers={"User-Agent": UA})
                with urlopen(r, timeout=10) as resp:
                    return url, f"{resp.status} {resp.reason or ''} (via GET)".strip()
            except Exception as e2:
                return url, f"HEAD {e.code} / GET {type(e2).__name__}: {e2}"
        return url, f"HTTP {e.code} {e.reason}"
    except URLError as e:
        return url, f"URL error: {e.reason}"
    except Exception as e:
        return url, f"{type(e).__name__}: {e}"


def main() -> None:
    urls: dict[str, list[str]] = {}
    for p in sorted(ROOT.glob("*.ipynb")):
        nb = json.load(open(p, encoding="utf-8"))
        for c in nb["cells"]:
            if c.get("cell_type") != "markdown":
                continue
            src = "".join(c["source"]) if isinstance(c["source"], list) else c["source"]
            for u in URL_RE.findall(src):
                # Strip trailing punctuation that isn't part of URL
                u = u.rstrip(".,;:!?)")
                urls.setdefault(u, []).append(p.name)

    unique = sorted(urls.keys())
    print(f"Found {len(unique)} unique URLs across {sum(len(v) for v in urls.values())} occurrences.\n")

    problems = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:
        for url, status in ex.map(check, unique):
            first = status.split()[0]
            ok = first.startswith("2") or first.startswith("3")
            if not ok:
                where = ", ".join(sorted(set(urls[url])))
                problems.append((url, status, where))

    if not problems:
        print("All URLs return 2xx/3xx.")
        return
    print(f"{len(problems)} problematic URLs:\n")
    for url, status, where in problems:
        print(f"  [{status}] {url}")
        print(f"      seen in: {where}")


if __name__ == "__main__":
    main()
