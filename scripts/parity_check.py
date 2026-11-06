#!/usr/bin/env python3
"""Check a built site against a parity checklist and print a verdict per item.

Usage: parity_check.py <parity.json> [--root DIR] [--offline] [--out REPORT.md]

parity.json lists the items to supervise. Each item has an id, a title, the benchmark
it comes from, and one or more checks. An item passes only when every check passes.
Paths in checks are relative to --root (default: the folder holding parity.json).

Check types
  exists        path                         file or folder exists
  contains      path, pattern                regex found in file
  absent        path, pattern                regex not found in file
  each          glob, pattern, [min_ratio]   regex found in at least min_ratio (default 1.0) of matched files
  none          glob, pattern                regex found in no matched file
  count         glob, [at_least | at_least_rows_of]   number of matched files >= a number, or >= rows in a CSV
  json          path, key, op, value         op: eq, ne, ge, le on a top-level JSON key
  upstream      repo, path, local_json, key  a GitHub file's latest commit is the one recorded in local_json[key]
                                             (UNKNOWN with --offline or without network; set GITHUB_TOKEN to avoid rate limits)
Exit code: 0 when every item passes, 1 when any item fails, 2 on a bad checklist.
"""
import csv
import glob as globmod
import json
import os
import re
import ssl
import sys
import urllib.request


def read(path):
    try:
        return open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return None


def files(root, pattern):
    return sorted(globmod.glob(os.path.join(root, pattern), recursive=True))


def run_check(c, root, offline):
    """Return (status, evidence). status: PASS, FAIL or UNKNOWN."""
    t = c["type"]
    p = os.path.join(root, c.get("path", ""))
    if t == "exists":
        return ("PASS" if os.path.exists(p) else "FAIL"), c["path"]
    if t in ("contains", "absent"):
        text = read(p)
        if text is None:
            return "FAIL", f"missing file {c['path']}"
        m = re.search(c["pattern"], text)
        ok = bool(m) if t == "contains" else not m
        where = f"found {m.group(0)[:60]!r}" if m else "not found"
        return ("PASS" if ok else "FAIL"), f"{c['path']}: /{c['pattern']}/ {where}"
    if t in ("each", "none"):
        fs = files(root, c["glob"])
        if not fs:
            return "FAIL", f"no files match {c['glob']}"
        rx = re.compile(c["pattern"])
        hits = [f for f in fs if rx.search(read(f) or "")]
        if t == "each":
            need = c.get("min_ratio", 1.0)
            ratio = len(hits) / len(fs)
            miss = [os.path.relpath(f, root) for f in fs if f not in set(hits)][:3]
            return ("PASS" if ratio >= need else "FAIL"), f"{len(hits)}/{len(fs)} files match /{c['pattern']}/" + (f"; e.g. missing in {miss}" if miss else "")
        return ("PASS" if not hits else "FAIL"), f"{len(hits)}/{len(fs)} files contain /{c['pattern']}/" + (f": {[os.path.relpath(f, root) for f in hits[:3]]}" if hits else "")
    if t == "count":
        n = len(files(root, c["glob"]))
        if "at_least_rows_of" in c:
            need = sum(1 for _ in csv.DictReader(open(os.path.join(root, c["at_least_rows_of"]), encoding="utf-8")))
        else:
            need = c["at_least"]
        return ("PASS" if n >= need else "FAIL"), f"{n} files for {c['glob']}, need >= {need}"
    if t == "json":
        data = json.loads(read(p) or "{}")
        v, want, op = data.get(c["key"]), c["value"], c.get("op", "eq")
        ok = {"eq": v == want, "ne": v != want, "ge": v is not None and v >= want, "le": v is not None and v <= want}[op]
        return ("PASS" if ok else "FAIL"), f"{c['path']}[{c['key']}] = {v!r}, want {op} {want!r}"
    if t == "upstream":
        local = json.loads(read(os.path.join(root, c["local_json"])) or "{}").get(c["key"], "")
        if offline:
            return "UNKNOWN", f"offline; local {c['key']} = {local}"
        url = f"https://api.github.com/repos/{c['repo']}/commits?path={c['path']}&per_page=1"
        try:
            headers = {"User-Agent": "ivan-parity", "Accept": "application/vnd.github+json"}
            if os.environ.get("GITHUB_TOKEN"):  # optional: avoids the low anonymous rate limit
                headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
            req = urllib.request.Request(url, headers=headers)
            ca = os.environ.get("SSL_CERT_FILE") or ("/etc/ssl/cert.pem" if os.path.exists("/etc/ssl/cert.pem") else None)
            sha = json.load(urllib.request.urlopen(req, timeout=20, context=ssl.create_default_context(cafile=ca)))[0]["sha"]
        except Exception as ex:  # no network, rate limit
            return "UNKNOWN", f"could not reach GitHub ({ex.__class__.__name__}); local {c['key']} = {local}"
        ok = bool(local) and sha.startswith(local)
        return ("PASS" if ok else "FAIL"), f"upstream {c['repo']}:{c['path']} at {sha[:7]}, site built from {local or 'nothing recorded'}"
    raise ValueError(f"unknown check type {t}")


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    spec_path = args[0]
    root = args[args.index("--root") + 1] if "--root" in args else os.path.dirname(os.path.abspath(spec_path))
    out = args[args.index("--out") + 1] if "--out" in args else None
    offline = "--offline" in args
    spec = json.load(open(spec_path, encoding="utf-8"))
    lines = [f"# {spec.get('title', 'Parity check')}", "", f"Benchmark: {spec.get('benchmark', '')}", "",
             "| # | Item | Verdict | Evidence |", "|---|---|---|---|"]
    failed = unknown = 0
    for i, item in enumerate(spec["items"], 1):
        results = [run_check(c, root, offline) for c in item["checks"]]
        statuses = [s for s, _ in results]
        verdict = "FAIL" if "FAIL" in statuses else ("UNKNOWN" if "UNKNOWN" in statuses else "PASS")
        failed += verdict == "FAIL"
        unknown += verdict == "UNKNOWN"
        ev = "<br>".join(f"{s}: {e}".replace("|", "\\|") for s, e in results)
        lines.append(f"| {i} | {item['title']} | **{verdict}** | {ev} |")
    total = len(spec["items"])
    lines += ["", f"{total - failed - unknown} of {total} items pass, {failed} fail, {unknown} unknown."]
    report = "\n".join(lines) + "\n"
    print(report)
    if out:
        open(out, "w", encoding="utf-8").write(report)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
