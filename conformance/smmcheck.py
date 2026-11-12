#!/usr/bin/env python3
"""smmcheck — test whether an SMM panel actually implements the standard API.

Read-only probes only: it never places an order, never spends balance and never
changes state. That is deliberate - it must be safe to point at any panel,
including one you do not administer.

    python3 smmcheck.py --base https://panel.example --key YOUR_KEY
    python3 smmcheck.py --base https://panel.example --key K --version v2 --json

Exit code 0 when every probe passed, 1 otherwise. Standard library only.
"""
import argparse, json, sys, time, urllib.parse, urllib.request

SPEC = json.load(open(__file__.replace("conformance/smmcheck.py", "spec/smm-panel-api.json")))

# Only the actions that cannot mutate state. status needs a real order id, so it
# is probed with a deliberately invalid one: the shape of the *error* is the test.
PROBES = ["services", "balance"]


def call(base, version, key, action, **params):
    q = {"key": key, "action": action, **params}
    url = f"{base.rstrip('/')}/{version}?{urllib.parse.urlencode(q)}"
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(urllib.request.Request(
                url, headers={"User-Agent": "smmcheck/1.0", "Accept": "application/json"}),
                timeout=20) as r:
            body = r.read().decode("utf-8", "replace")
            return r.status, body, (time.monotonic() - t0) * 1000
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace"), (time.monotonic() - t0) * 1000
    except Exception as e:
        return 0, f"__transport__: {e}", (time.monotonic() - t0) * 1000


def check_services(body):
    try:
        d = json.loads(body)
    except Exception:
        return False, "not JSON"
    if isinstance(d, dict):
        return False, f"expected an array, got an object ({list(d)[:3]})"
    if not d:
        return False, "empty service list"
    need = {"service", "name", "category", "rate", "min", "max"}
    missing = need - set(d[0])
    if missing:
        return False, f"first service missing {sorted(missing)}"
    return True, f"{len(d)} services, {len(d[0])} fields each"


def check_balance(body):
    try:
        d = json.loads(body)
    except Exception:
        return False, "not JSON"
    if not isinstance(d, dict):
        return False, "expected an object"
    if "error" in d:
        return None, f"auth rejected: {d['error']}"
    if "balance" not in d:
        return False, f"no balance field ({list(d)[:4]})"
    if "currency" not in d:
        return False, "balance present but no currency"
    return True, f"{d['balance']} {d['currency']}"


CHECKS = {"services": check_services, "balance": check_balance}


def probe_all(base, version, key):
    """Run every read-only probe. Shared by the single-panel and batch modes."""
    results = []
    for action in PROBES:
        code, body, ms = call(base, version, key, action)
        ok, detail = CHECKS[action](body) if code == 200 else (False, f"HTTP {code}")
        results.append({"action": action, "http": code, "ok": ok, "ms": round(ms),
                        "detail": detail})

    # The error envelope is part of the contract, so probe it explicitly.
    code, body, ms = call(base, version, key, "status", order="999999999999")
    try:
        env = json.loads(body)
        envelope_ok = isinstance(env, dict) and ("error" in env or "status" in env)
    except Exception:
        envelope_ok = False
    results.append({"action": "status(unknown id)", "http": code, "ok": envelope_ok,
                    "ms": round(ms),
                    "detail": "error envelope present" if envelope_ok else "no {\"error\": ...} envelope"})
    return results


def run_batch(path, version):
    """Compare panels from a `name,base,key` file - the choosing-a-provider case."""
    rows = []
    for raw in open(path, encoding="utf-8"):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 3:
            rows.append({"name": parts[0], "ok": False, "detail": "malformed line"})
            continue
        name, base, key = parts[0], parts[1], ",".join(parts[2:])
        res = probe_all(base, version, key)
        passed = sum(1 for r in res if r["ok"])
        worst = max(r["ms"] for r in res)
        failed = [r["action"] for r in res if not r["ok"]]
        rows.append({"name": name, "passed": passed, "total": len(res),
                     "ok": passed == len(res), "worst_ms": worst,
                     "detail": "ok" if not failed else "failed: " + ", ".join(failed)})
    w = max((len(r["name"]) for r in rows), default=4)
    print(f"\n{'panel':{w}}  result      pass  latency  detail")
    print("-" * (w + 42))
    for r in rows:
        mark = "compliant" if r["ok"] else "NOT compliant"
        latency = f"{r.get('worst_ms', 0)}ms"
        print(f"{r['name']:{w}}  {mark:12s}  {r.get('passed', 0)}/{r.get('total', 3)}  "
              f"{latency:>7s}  {r['detail']}")
    print()
    return 0 if all(r["ok"] for r in rows) else 1


def main():
    ap = argparse.ArgumentParser(description="Check an SMM panel against the documented API.")
    ap.add_argument("--base", help="panel base URL, e.g. https://panel.example")
    ap.add_argument("--key", help="your API key")
    ap.add_argument("--version", default="v1", choices=["v1", "v2"])
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--batch", metavar="FILE",
                    help="compare panels from a file of name,base,key lines")
    a = ap.parse_args()

    if a.batch:
        return run_batch(a.batch, a.version)
    if not a.base or not a.key:
        ap.error("--base and --key are required unless --batch is used")

    results = probe_all(a.base, a.version, a.key)

    passed = sum(1 for r in results if r["ok"])
    verdict = passed == len(results)

    if a.json:
        print(json.dumps({"base": a.base, "version": a.version, "compliant": verdict,
                          "passed": passed, "total": len(results), "probes": results}, indent=2))
    else:
        print(f"\n{a.base}  ({a.version})\n" + "-" * 62)
        for r in results:
            mark = {True: "PASS", False: "FAIL", None: "SKIP"}[r["ok"]]
            print(f"  {mark}  {r['action']:22s} {r['http']:>3}  {r['ms']:>5}ms  {r['detail']}")
        print("-" * 62)
        print(f"  {passed}/{len(results)} probes passed -> "
              f"{'compliant' if verdict else 'NOT compliant'}\n")
    return 0 if verdict else 1


if __name__ == "__main__":
    sys.exit(main())
