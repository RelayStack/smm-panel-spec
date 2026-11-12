"""A typed, dependency-free SMM Panel API client (v1 and v2).

    from smm_panel import Panel
    p = Panel("https://panel.example", "YOUR_KEY")
    for s in p.services():
        print(s.service, s.name, s.rate)

Deliberate choices:
  * stdlib only - panels are reachable from shared hosts where you cannot pip install.
  * returns `Decimal` for money, never float.
  * raises `PanelError` on the {"error": ...} envelope instead of returning it,
    because a business error that looks like data is how balances get lost.
"""
from decimal import Decimal
import json, urllib.parse, urllib.request


class PanelError(RuntimeError):
    """A business error returned in the HTTP 200 envelope."""


class Panel:
    def __init__(self, base_url, key, version="v1", timeout=30):
        self.base = base_url.rstrip("/")
        self.key = key
        self.version = version
        self.timeout = timeout

    def _call(self, action, **params):
        q = {"key": self.key, "action": action}
        q.update({k: v for k, v in params.items() if v is not None})
        url = f"{self.base}/api/{self.version}?{urllib.parse.urlencode(q)}"
        req = urllib.request.Request(url, headers={
            "Accept": "application/json", "User-Agent": "smm-panel-client/1.0"})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            payload = json.loads(r.read().decode("utf-8", "replace"))
        if isinstance(payload, dict) and "error" in payload:
            raise PanelError(payload["error"])
        return payload

    # --- read
    def services(self):
        return self._call("services")

    def balance(self):
        d = self._call("balance")
        return Decimal(str(d["balance"])), d.get("currency", "")

    def status(self, order):
        return self._call("status", order=order)

    def status_many(self, orders):
        return self._call("status", orders=",".join(str(o) for o in orders))

    def orders(self, limit=100, offset=0):
        return self._call("orders", limit=limit, offset=offset)["orders"]

    # --- write
    def add(self, service, link, quantity, runs=None, interval=None):
        return self._call("add", service=service, link=link, quantity=quantity,
                          runs=runs, interval=interval)["order"]

    def cancel(self, orders):
        return self._call("cancel", orders=",".join(str(o) for o in orders))["cancel"]

    def refill(self, order):
        return self._call("refill", order=order)["refill"]
