# SMM Panel API — v1 and v2, written down

Every SMM panel and most reseller tools speak the same API: form-encoded POSTs to
`/api/v1`, a `key` parameter, an `action` name, JSON back. It is not published by
anyone. It exists because one panel shipped it years ago and everybody copied the
shape.

This repository is that format, written down and made testable.

**Live board:** https://relaystack.github.io/smm-panel-spec/ — press *Run conformance* and watch
the three read-only probes land.

| what | file | what it is for |
|---|---|---|
| The spec | [`SPEC.md`](SPEC.md) | normative prose, field by field |
| The spec, machine-readable | [`spec/smm-panel-api.json`](spec/smm-panel-api.json) | generate clients, validate responses |
| A conformance tester | [`conformance/smmcheck.py`](conformance/smmcheck.py) | does this panel actually implement it? |
| A mock panel | [`mock/server.py`](mock/server.py) | build against it without a key or money |
| Clients | [`clients/`](clients/) | Python, PHP and Node, all dependency-free |
| A GitHub Action | [`action.yml`](action.yml) | run the check inside your own CI |

## Why this exists

The format is stable enough to be a specification and undocumented enough that
every implementation guesses. The visible cost is in reseller tooling: a
multi-panel dashboard has to special-case each panel, because "does it return
`order` as a string or a number", "does `status` accept a comma list" and "is a
failed order an HTTP error or a 200 with `error`" all differ.

Write it down once and those questions stop being guesswork.

## The eight actions

| action | versions | mutates | returns |
|---|---|---|---|
| `services` | v1, v2 | no | array of services (`service`, `name`, `category`, `rate`, `min`, `max`, `type`) |
| `balance` | v1, v2 | no | `{balance, currency}` |
| `status` | v1, v2 | no | `{order, status, charge, start_count, remains}`; a comma list of `orders` returns a map |
| `add` | v1, v2 | **yes** | `{status: "success", order: <id>}` |
| `orders` | v2 | no | order history array |
| `cancel` | v2 | **yes** | `{status: "success", cancel: <count>}` |
| `refill` | v2 | **yes** | `{status: "success", refill: <id>}` |
| `refill_status` | v2 | no | `{status: "success", refill: <status>}` |

Three conventions cause most of the bugs, and all three are in the spec:

1. **Business errors are HTTP 200.** `{"error": "Incorrect order ID"}` is a
   successful HTTP response. Check the body, not the status code.
2. **Money and counters may be strings or numbers.** `"1.02"` and `1.02` both
   appear in the wild, in the same field, across versions. Parse to a decimal,
   never to a float.
3. **`add` is not delivery.** A success response means the order was accepted and
   the balance debited. Delivery is asynchronous; poll `status`.

Full details, including the error envelope and the `status` value set, are in
[`SPEC.md`](SPEC.md).

## Test a panel

Read-only. It never places an order, never spends balance, never changes state —
point it at any panel, including one you do not administer.

```bash
python3 conformance/smmcheck.py --base https://panel.example --key YOUR_API_KEY
```

```
https://panel.example  (v1)
--------------------------------------------------------------
  PASS  services               200     24ms  2 services, 8 fields each
  PASS  balance                200      1ms  24.56 USD
  PASS  status(unknown id)     200      1ms  error envelope present
--------------------------------------------------------------
  3/3 probes passed -> compliant
```

`--json` gives the same result as machine-readable output. Exit code is 0 only
when every probe passes, so it drops straight into CI.

The third probe is the useful one: it asks for an order id that cannot exist and
checks that the panel answers with an `{"error": ...}` envelope rather than a
stack trace, an empty body or an HTML error page.

## Compare panels

Picking a provider is the same question across several panels. Feed it a file:

```bash
cat > panels.csv <<'EOF'
# name,base,key
panel-a,https://a.example,YOUR_KEY
panel-b,https://b.example,YOUR_KEY
EOF
python3 conformance/smmcheck.py --batch panels.csv
```

```
panel    result         pass  latency  detail
------------------------------------------------------
panel-a  compliant       3/3     24ms  ok
panel-b  NOT compliant   1/3      1ms  failed: services, balance
```

Same read-only probes, same exit code.

## Build against the mock

```bash
python3 mock/server.py --port 8080
curl "http://127.0.0.1:8080/api/v1?key=test&action=balance"
```

Two services, one account, in-memory orders that move `pending → inprogress →
completed` on a timer. Enough to develop polling, multi-status and cancel
handling without a real panel, a real key or real money. State resets on
restart; nothing it does costs anything.

## Clients

Three, all dependency-free, all the same shape: money stays a string, the error
envelope throws instead of returning.

| language | file | note |
|---|---|---|
| Python | [`clients/python/smm_panel.py`](clients/python/smm_panel.py) | `Decimal` for money |
| PHP | [`clients/php/SmmPanel.php`](clients/php/SmmPanel.php) | cURL, no Composer needed |
| Node 18+ | [`clients/node/smm-panel.js`](clients/node/smm-panel.js) | global `fetch`, ESM |

```python
from smm_panel import Panel, PanelError

p = Panel("https://panel.example", "YOUR_KEY")
print(p.balance())                                   # (Decimal('24.56'), 'USD')
order = p.add(service=1, link="https://instagram.com/p/x", quantity=1000)
print(p.status(order))                               # {'status': 'inprogress', ...}
```

## Use it in CI

The repository is a composite GitHub Action, so the check can live next to the
integration it protects:

```yaml
- uses: RelayStack/smm-panel-spec@main
  with:
    base_url: ${{ secrets.PANEL_URL }}
    api_key: ${{ secrets.PANEL_KEY }}
```

Read-only, so a nightly run cannot cost anything beyond the requests themselves.

## Which panels implement this

The conformance tester answers that per panel, because the field is inconsistent
by design — most panels ship it as a reseller feature and document it in a
support ticket. [SMMScout](https://smmscout.com/market-report/) measures API
latency and endpoint coverage across the panels it tracks; its
[market report](https://smmscout.com/market-report/) is where those numbers live.

## Contributing

If your panel differs, that is the most valuable thing you can send: open an
issue with the request, the response and the panel name. Divergence is the
content this spec exists to capture.

MIT licensed.
