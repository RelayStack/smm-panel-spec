#!/usr/bin/env python3
"""The spec is only worth publishing if it actually validates something.
Starts the mock panel, points the conformance checker at it, and asserts a pass.
Also asserts that a broken panel fails - otherwise a green result means nothing.
"""
import json, os, subprocess, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PORT = 8123


def run_check(base):
    p = subprocess.run([sys.executable, f"{ROOT}/conformance/smmcheck.py",
                        "--base", base, "--key", "test", "--json"],
                       capture_output=True, text=True)
    return p.returncode, json.loads(p.stdout)


def main():
    srv = subprocess.Popen([sys.executable, f"{ROOT}/mock/server.py", "--port", str(PORT)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{PORT}"
    try:
        for _ in range(50):
            try:
                urllib.request.urlopen(f"{base}/api/v1?key=test&action=balance", timeout=1)
                break
            except Exception:
                time.sleep(0.1)

        code, out = run_check(base)
        assert code == 0, f"mock should be compliant, got {code}: {out}"
        assert out["compliant"] and out["passed"] == out["total"], out
        print(f"PASS compliant mock: {out['passed']}/{out['total']} probes")

        # The same checker must reject a panel that lies about the format.
        bad = subprocess.Popen([sys.executable, "-c",
                                f"import http.server as h\n"
                                f"class Q(h.BaseHTTPRequestHandler):\n"
                                f"    def do_GET(s):\n"
                                f"        b=b'{{\"ok\":true}}'\n"
                                f"        s.send_response(200);s.send_header('Content-Length',str(len(b)));s.end_headers();s.wfile.write(b)\n"
                                f"    def log_message(s,*a):pass\n"
                                f"h.HTTPServer(('127.0.0.1',{PORT + 1}),Q).serve_forever()"])
        try:
            time.sleep(0.8)
            code, out = run_check(f"http://127.0.0.1:{PORT + 1}")
            assert code == 1 and not out["compliant"], f"broken panel must fail, got {out}"
            print(f"PASS rejects non-compliant panel: {out['passed']}/{out['total']} probes")
        finally:
            bad.terminate()
    finally:
        srv.terminate()
    print("conformance self-test OK")


if __name__ == "__main__":
    main()
