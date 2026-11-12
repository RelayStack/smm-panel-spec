/**
 * A dependency-free SMM Panel API client (v1 and v2). Node 18+ (global fetch).
 *
 *   import { Panel } from "./smm-panel.js";
 *   const p = new Panel("https://panel.example", process.env.SMM_KEY);
 *   console.log(await p.balance());
 *
 * Money stays a string: "1.02" as a Number is 1.0200000000000002 after enough
 * arithmetic, and this client is used for billing. Parse at the edge if you need
 * arithmetic, and do that in integer minor units.
 */

export class PanelError extends Error {}

export class Panel {
  constructor(baseUrl, key, { version = "v1", timeout = 30000 } = {}) {
    this.base = baseUrl.replace(/\/+$/, "");
    this.key = key;
    this.version = version;
    this.timeout = timeout;
  }

  async call(action, params = {}) {
    const q = new URLSearchParams({ key: this.key, action });
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null) q.set(k, String(v));
    }
    const url = `${this.base}/api/${this.version}?${q}`;
    const res = await fetch(url, {
      headers: { Accept: "application/json", "User-Agent": "smm-panel-client/1.0" },
      signal: AbortSignal.timeout(this.timeout),
    });
    const body = await res.text();
    let data;
    try {
      data = JSON.parse(body);
    } catch {
      throw new PanelError(`response was not JSON: ${body.slice(0, 120)}`);
    }
    if (data && typeof data === "object" && "error" in data) throw new PanelError(data.error);
    return data;
  }

  services() { return this.call("services"); }
  balance() { return this.call("balance"); }
  status(order) { return this.call("status", { order }); }
  statusMany(orders) { return this.call("status", { orders: orders.join(",") }); }
  async orders({ limit = 100, offset = 0 } = {}) {
    return (await this.call("orders", { limit, offset })).orders ?? [];
  }
  async add(service, link, quantity, { runs, interval } = {}) {
    return (await this.call("add", { service, link, quantity, runs, interval })).order;
  }
  async cancel(orders) { return (await this.call("cancel", { orders: orders.join(",") })).cancel; }
  async refill(order) { return (await this.call("refill", { order })).refill; }
}
