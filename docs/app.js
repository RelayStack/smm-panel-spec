// The board: replay a captured conformance run, and open any row to its wire shapes.
// No dependencies, no build step. The numbers come from report.json, which is the
// output of running conformance/smmcheck.py against the bundled mock server.

const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;

/* ---------- clock ---------- */

const clock = document.getElementById("clock");
const tick = () => {
  clock.textContent = new Date().toLocaleTimeString("en-GB", { hour12: false });
};
tick();
setInterval(tick, 1000);

/* ---------- row details ---------- */

document.querySelectorAll(".b__toggle").forEach((btn) => {
  btn.addEventListener("click", () => {
    const panel = document.getElementById(btn.getAttribute("aria-controls"));
    const open = btn.getAttribute("aria-expanded") === "true";
    btn.setAttribute("aria-expanded", String(!open));
    panel.hidden = open;
  });
});

/* ---------- copy ---------- */

const copy = document.getElementById("copy");
copy.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(copy.dataset.copy);
    copy.dataset.done = "1";
    copy.querySelector("span").textContent = "Copied";
  } catch {
    copy.querySelector("span").textContent = "Copy failed";
  }
  setTimeout(() => {
    delete copy.dataset.done;
    copy.querySelector("span").textContent = "Copy";
  }, 1800);
});

/* ---------- the run ---------- */

const run = document.getElementById("runbtn");
const say = document.getElementById("say");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function flap(el, text, state) {
  if (el.textContent === text && el.dataset.state === state) return;
  el.dataset.state = state;
  if (reduce) {
    el.textContent = text;
    return;
  }
  el.animate(
    [
      { transform: "translateY(0)", opacity: 1, filter: "blur(0)" },
      { transform: "translateY(-42%)", opacity: 0, filter: "blur(2px)" },
    ],
    { duration: 110, easing: "cubic-bezier(.4,0,.9,.6)" }
  ).finished.then(() => {
    el.textContent = text;
    el.animate(
      [
        { transform: "translateY(42%)", opacity: 0, filter: "blur(2px)" },
        { transform: "translateY(0)", opacity: 1, filter: "blur(0)" },
      ],
      { duration: 150, easing: "cubic-bezier(.1,.8,.2,1)" }
    );
  });
}

function cellFor(action) {
  const row = document.querySelector(`.b__row[data-action="${CSS.escape(action)}"]`);
  return row && {
    flap: row.querySelector(".flap"),
    lat: row.querySelector(".num"),
    note: row.querySelector(".b__note"),
  };
}

run.addEventListener("click", async () => {
  run.disabled = true;
  run.textContent = "Running";
  say.dataset.tone = "";
  say.textContent = "Probing the three read-only actions…";

  let report;
  try {
    const res = await fetch(`report.json?t=${Date.now()}`, { cache: "no-store" });
    if (!res.ok) throw new Error(`report.json returned ${res.status}`);
    report = await res.json();
  } catch (err) {
    say.dataset.tone = "bad";
    say.textContent = `Could not load the captured report (${err.message}). Open this page over HTTP, not from the filesystem.`;
    run.disabled = false;
    run.textContent = "Run conformance";
    return;
  }

  for (const probe of report.probes) {
    const action = probe.action.startsWith("status") ? "status" : probe.action;
    const c = cellFor(action);
    if (!c) continue;
    flap(c.flap, "probing", "busy");
    if (c.note) c.note.textContent = "…";
    await sleep(reduce ? 0 : 420 + probe.ms);
    flap(c.flap, probe.ok ? "pass" : "fail", probe.ok ? "pass" : "fail");
    c.lat.textContent = `${probe.ms} ms`;
    c.lat.dataset.set = "1";
    if (c.note) c.note.textContent = probe.detail;
    await sleep(reduce ? 0 : 160);
  }

  const total = report.probes.reduce((n, p) => n + p.ms, 0);
  say.dataset.tone = report.compliant ? "ok" : "bad";
  say.textContent = report.compliant
    ? `${report.passed}/${report.total} probes passed in ${total} ms against the bundled mock. The other five actions write, so they were never called.`
    : `${report.total - report.passed} of ${report.total} probes failed. A non-compliant panel is the case this tool exists for — the report names the shape that broke.`;

  run.disabled = false;
  run.textContent = "Run again";
});
