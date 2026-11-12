#!/usr/bin/env python3
"""A mock SMM panel that implements the documented API, so front-ends and
reseller tools can be developed without a real panel, a real key or real money.

    python3 mock/server.py --port 8080
    curl "http://127.0.0.1:8080/api/v1?key=test&action=balance"

State lives in memory and resets on restart. Orders progress pending ->
inprogress -> completed on a timer, which is what makes it useful for testing
polling and multi-status code paths. Standard library only.
"""
import argparse, json, threading, time, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

KEY = "test"
SERVICES = [
    {"service": 1, "name": "Instagram Followers [15K]", "category": "Instagram",
     "rate": "1.02", "min": "500", "max": "10000", "type": "default", "dripfeed": 1},
    {"service": 2, "name": "YouTube Views [HR]", "category": "YouTube",
     "rate": "0.92", "min": "1000", "max": "1000000", "type": "default", "dripfeed": 0},
]
ORDERS, LOCK, NEXT = {}, threading.Lock(), [1000]


def advance():
    """Move orders along so polling code sees real transitions."""
    while True:
        time.sleep(2)
        with LOCK:
            for o in ORDERS.values():
                o["status"] = {"pending": "inprogress",
                               "inprogress": "completed"}.get(o["status"], o["status"])


def handle(params):
    if params.get("key") != KEY:
        return 200, {"error": "Incorrect API key"}
    action = params.get("action")
    if action == "services":
        return 200, SERVICES
    if action == "balance":
        return 200, {"status": "success", "balance": "24.56", "currency": "USD"}
    if action == "add":
        if not params.get("link"):
            return 200, {"error": "Invalid link"}
        with LOCK:
            NEXT[0] += 1
            oid = NEXT[0]
            ORDERS[oid] = {"order": oid, "service_id": int(params.get("service", 1)),
                           "service": "Instagram Followers", "link": params["link"],
                           "quantity": int(params.get("quantity", 1000)),
                           "charge": "1.02", "status": "pending",
                           "start_count": "0", "remains": params.get("quantity", "1000"),
                           "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        return 200, {"status": "success", "order": oid}
    if action == "status":
        if "orders" in params:
            out = {}
            for one in str(params["orders"]).split(","):
                one = one.strip()
                o = ORDERS.get(int(one)) if one.isdigit() else None
                # Per SPEC §5.3 the multi form maps a failure to a bare string.
                out[one] = dict(o) if o else "Incorrect order ID"
            return 200, out
        o = ORDERS.get(int(params.get("order", 0)))
        return 200, dict(o) if o else {"error": "Incorrect order ID"}
    if action == "orders":
        return 200, {"status": "success", "orders": sorted(ORDERS.values(), key=lambda o: -o["order"])}
    if action == "cancel":
        n = 0
        for one in str(params.get("orders", "")).split(","):
            o = ORDERS.get(int(one.strip() or 0))
            if o and o["status"] == "pending":
                o["status"], n = "canceled", n + 1
        return 200, {"status": "success", "cancel": n}
    if action == "refill":
        o = ORDERS.get(int(params.get("order", 0)))
        return 200, {"status": "success", "refill": 7} if o else {"error": "Incorrect order ID"}
    if action == "refill_status":
        return 200, {"status": "success", "refill": params.get("refill", "0")}
    return 200, {"error": f"Unknown action: {action}"}


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _serve(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        params = {k: v[0] for k, v in q.items()}
        n = int(self.headers.get("Content-Length") or 0)
        if n:
            params.update({k: v[0] for k, v in
                           urllib.parse.parse_qs(self.rfile.read(n).decode()).items()})
        code, payload = handle(params)
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    do_GET = _serve
    do_POST = _serve

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8080)
    a = ap.parse_args()
    threading.Thread(target=advance, daemon=True).start()
    print(f"mock SMM panel on http://127.0.0.1:{a.port}  (key: {KEY})")
    ThreadingHTTPServer(("127.0.0.1", a.port), H).serve_forever()
