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


def main():
    ap = argparse.ArgumentParser(description="Check an SMM panel against the documented API.")
    ap.add_argument("--base", required=True, help="panel base URL, e.g. https://panel.example")
    ap.add_argument("--key", required=True, help="your API key")
    ap.add_argument("--version", default="v1", choices=["v1", "v2"])
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    a = ap.parse_args()

    results = []
    for action in PROBES:
        code, body, ms = call(a.base, a.version, a.key, action)
        ok, detail = CHECKS[action](body) if code == 200 else (False, f"HTTP {code}")
        results.append({"action": action, "http": code, "ok": ok, "ms": round(ms),
                        "detail": detail})

    # The error envelope is part of the contract, so probe it explicitly.
    code, body, ms = call(a.base, a.version, a.key, "status", order="999999999999")
    try:
        env = json.loads(body)
        envelope_ok = isinstance(env, dict) and ("error" in env or "status" in env)
    except Exception:
        envelope_ok = False
    results.append({"action": "status(unknown id)", "http": code, "ok": envelope_ok,
                    "ms": round(ms),
                    "detail": "error envelope present" if envelope_ok else "no {\"error\": ...} envelope"})

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
