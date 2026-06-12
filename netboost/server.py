"""NetBoost - Web Server Backend.

Serves the dashboard UI and provides JSON API endpoints.
Zero dependencies - uses Python built-in http.server.
"""
import json
import os
import sys
import threading
import webbrowser
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from netboost.core import scanner, speedtest, diagnosis, optimizer, compare
from netboost import utils

_state = {
    "scan_results": None,
    "speed_before": None,
    "speed_after": None,
    "report": None,
    "actions": [],
}


class NetBoostHandler(SimpleHTTPRequestHandler):
    """HTTP handler for the NetBoost web dashboard."""

    def __init__(self, *args, **kwargs):
        self.web_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
        super().__init__(*args, directory=self.web_dir, **kwargs)

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self._handle_api(parsed.path[5:], None)
        else:
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length) if content_length else b""
            data = json.loads(body) if body else None
            self._handle_api(parsed.path[5:], data)
        else:
            self.send_error(404)

    def _handle_api(self, endpoint, data):
        try:
            if endpoint == "scan":
                result = self._do_scan()
            elif endpoint == "speedtest":
                result = self._do_speedtest()
            elif endpoint == "diagnose":
                result = self._do_diagnose()
            elif endpoint == "optimize":
                result = self._do_optimize(data)
            elif endpoint == "optimize-all":
                result = self._do_optimize_all()
            elif endpoint == "retest":
                result = self._do_retest()
            elif endpoint == "rollback":
                result = self._do_rollback()
            elif endpoint == "status":
                result = {"status": "ready"}
            else:
                self.send_error(404)
                return
            self._json_response(result)
        except Exception as e:
            self._json_response({"error": str(e)}, 500)

    def _json_response(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _do_scan(self):
        results = scanner.scan_all()
        _state["scan_results"] = results
        return results

    def _do_speedtest(self):
        results = speedtest.run_speedtest()
        _state["speed_before"] = results
        return results

    def _do_diagnose(self):
        scan_res = _state.get("scan_results") or {}
        speed_res = _state.get("speed_before")
        report = diagnosis.diagnose(scan_res, speed_res)
        _state["report"] = report
        actions = optimizer.generate_actions(scan_res, report)
        _state["actions"] = actions
        result = report.to_dict()
        result["actions"] = [a.to_dict() for a in actions]
        return result

    def _do_optimize(self, data):
        index = data.get("index", 0) if data else 0
        actions = _state.get("actions", [])
        if index >= len(actions):
            return {"success": False, "message": "invalid action index"}
        action = actions[index]
        success, msg = optimizer.execute_action(action)
        return {"success": success, "message": msg}

    def _do_optimize_all(self):
        actions = _state.get("actions", [])
        results = []
        success_count = 0
        for action in actions:
            success, msg = optimizer.execute_action(action)
            results.append({"success": success, "message": msg})
            if success:
                success_count += 1
        return {"total": len(actions), "success_count": success_count, "results": results}

    def _do_retest(self):
        speed_after = speedtest.run_speedtest()
        _state["speed_after"] = speed_after
        before_data = {}
        after_data = {}
        if _state.get("speed_before"):
            before_data.update(_state["speed_before"])
        if _state.get("report"):
            before_data["score"] = _state["report"].score
            before_data["dns_avg_ms"] = _state["report"].metrics.get("dns_avg_ms")
        after_data.update(speed_after)
        new_scan = scanner.scan_all()
        new_report = diagnosis.diagnose(new_scan, speed_after)
        after_data["score"] = new_report.score
        after_data["dns_avg_ms"] = new_report.metrics.get("dns_avg_ms")
        comparison = compare.compare(before_data, after_data)
        return {"speed": speed_after, "comparison": comparison}

    def _do_rollback(self):
        rollback_file = os.path.join(os.path.expanduser("~"), "netboost_rollback")
        rollback_file += ".bat" if utils.IS_WIN else ".sh"
        if os.path.exists(rollback_file):
            cmd = f'"{rollback_file}"' if utils.IS_WIN else f'bash "{rollback_file}"'
            utils.run_cmd(cmd, timeout=30)
            return {"success": True, "message": "all changes rolled back"}
        else:
            return {"success": False, "message": "no rollback file found"}


def start_server(port=7890, open_browser=True):
    """Start the web server and open browser."""
    server = HTTPServer(("127.0.0.1", port), NetBoostHandler)
    url = f"http://127.0.0.1:{port}"
    print(f"\n  NetBoost Dashboard")
    print(f"  {'=' * 36}")
    print(f"  {url}")
    print(f"  Ctrl+C to exit\n")
    if open_browser:
        def _open():
            time.sleep(0.5)
            webbrowser.open(url)
        threading.Thread(target=_open, daemon=True).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Stopped")
        server.shutdown()


if __name__ == "__main__":
    port = 7890
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    start_server(port)