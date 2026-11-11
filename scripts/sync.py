"""Pull the Data Center Power Index (DCPI) daily manifests and monthly files
from dchub.cloud into this repository, and check each manifest's fingerprint.

    python scripts/sync.py            # writes manifests/ and data/, prints a summary

Sources (public, no key):
    https://dchub.cloud/api/v1/data/dcpi-markets/manifests.json
    https://dchub.cloud/api/v1/data/dcpi-markets/manifest-<YYYY-MM-DD>.json
    https://dchub.cloud/api/v1/data/dcpi-markets/monthly-<YYYY-MM>.csv
    https://dchub.cloud/api/v1/data/dcpi-markets/<YYYY-MM-DD>.json   (to re-verify)

A closed day never changes, so a manifest already on disk is never rewritten.
If a re-fetched manifest disagrees with the stored one, the run fails instead
of overwriting it. While the archive is not public yet (HTTP 404, or 400 before
it deploys), the run writes nothing and exits 0.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys
import urllib.error
import urllib.request

BASE = "https://dchub.cloud/api/v1/data/dcpi-markets"
UA = "dcpi-history-sync/1.0 (+https://github.com/azmartone67/dcpi-history) (dc-own-run)"
ROOT = pathlib.Path(__file__).resolve().parent.parent


def get(url: str):
    """(status, bytes). 4xx is returned, not raised."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def canonical_sha256(rows, columns) -> str:
    """The manifest's canonical_form: one object per market sorted by
    market_slug, keys sorted, compact separators, UTF-8."""
    objs = sorted(({c: r.get(c) for c in columns} for r in rows), key=lambda o: o["market_slug"])
    raw = json.dumps(objs, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                     allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def verify(manifest: dict) -> str:
    """'ok', 'mismatch', or why it could not be checked."""
    status, body = get(f"{BASE}/{manifest['date']}.json")
    if status != 200:
        return f"day file HTTP {status}"
    rows = json.loads(body)["rows"]
    for r in rows:
        if r.get("composite_score") is not None:
            r["composite_score"] = float(r["composite_score"])
    got = canonical_sha256(rows, manifest["public_columns"])
    return "ok" if got == manifest["public_sha256"] else "mismatch"


def main() -> int:
    status, body = get(f"{BASE}/manifests.json")
    if status in (400, 404):
        # 404: the archive is still dark. 400: the server predates the archive
        # and reads "manifests" as a malformed date. Either way, nothing to pull.
        print(f"archive not public yet (manifests.json {status}); nothing written")
        return 0
    if status != 200:
        print(f"manifests.json HTTP {status}", file=sys.stderr)
        return 1
    index = json.loads(body)
    new, checked, failed = 0, {}, []
    for url in index["manifests"]:
        name = url.rsplit("/", 1)[1]
        day = name[len("manifest-"):-len(".json")]
        path = ROOT / "manifests" / day[:4] / name
        st, raw = get(url)
        if st != 200:
            failed.append(f"{day}: manifest HTTP {st}")
            continue
        m = json.loads(raw)
        if path.exists():
            old = json.loads(path.read_text(encoding="utf-8"))
            if old.get("public_sha256") != m.get("public_sha256"):
                failed.append(f"{day}: published fingerprint changed "
                              f"{old.get('public_sha256')} -> {m.get('public_sha256')}")
            continue
        result = verify(m)
        checked[day] = result
        if result == "mismatch":
            failed.append(f"{day}: public_sha256 does not match the day file")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(m, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        new += 1

    months = sorted({d[:7] for d in (u.rsplit("manifest-", 1)[1][:10] for u in index["manifests"])})
    wrote_months = []
    for month in months:
        st, raw = get(f"{BASE}/monthly-{month}.csv")
        if st != 200:
            continue
        path = ROOT / "data" / f"{month}.csv"
        if not path.exists() or path.read_bytes() != raw:
            path.write_bytes(raw)
            wrote_months.append(month)

    (ROOT / "manifests" / "index.json").write_text(
        json.dumps({"earliest": index["earliest"], "latest": index["latest"],
                    "no_snapshot": index["no_snapshot"]}, indent=2) + "\n", encoding="utf-8")
    print(f"manifests: {new} new; verified: "
          f"{sum(v == 'ok' for v in checked.values())} ok, "
          f"{sum(v not in ('ok', 'mismatch') for v in checked.values())} not checkable yet; "
          f"monthly files updated: {', '.join(wrote_months) or 'none'}")
    for f in failed:
        print("FAIL", f, file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
