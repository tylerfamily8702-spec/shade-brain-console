#!/usr/bin/env python3
"""
Shade-brain local status poller.

Run:
    python3 status-poller.py

GET /status returns health and recent journal output for Qdrant, LiteLLM,
Open WebUI, and Ollama. It listens on http://localhost:8765/status.
"""

import json
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import urlopen

PORT = 8765
HEALTH_TIMEOUT_SECONDS = 2
JOURNAL_TIMEOUT_SECONDS = 5

SERVICES = [
    {"name": "qdrant", "healthUrl": "http://localhost:6333/", "logUnit": "shade-qdrant"},
    {"name": "litellm", "healthUrl": "http://localhost:4000/health", "logUnit": "litellm"},
    {"name": "open-webui", "healthUrl": "http://localhost:8080/health", "logUnit": "open-webui"},
    {"name": "ollama", "healthUrl": "http://localhost:11434/", "logUnit": "ollama"},
]

ERROR_WORDS = (
    "error", "failed", "failure", "fatal", "panic", "exception", "traceback",
    "refused", "denied", "cannot", "can't", "critical", "segfault", "oom",
    "killed", "timeout", "timed out",
)


def check_health(url):
    """Return True only if the health endpoint returns HTTP 200."""
    try:
        with urlopen(url, timeout=HEALTH_TIMEOUT_SECONDS) as response:
            return response.getcode() == 200
    except Exception:
        return False


def select_log_lines(lines):
    """Prefer error-ish log lines when present. Otherwise return the latest 8 lines."""
    error_lines = [line for line in lines if any(word in line.lower() for word in ERROR_WORDS)]
    if error_lines:
        return error_lines[-20:]
    return lines[-8:]


def get_journal_logs(unit_name):
    """Read recent per-user systemd journal output for one service."""
    command = ["journalctl", "--user", "-u", unit_name, "-n", "20", "--no-pager"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=JOURNAL_TIMEOUT_SECONDS, check=False)
    except FileNotFoundError:
        return ["journalctl was not found on this machine."]
    except subprocess.TimeoutExpired:
        return [f"Timed out while reading journal logs for {unit_name}."]
    except Exception as error:
        return [f"Could not read journal logs for {unit_name}: {error}"]

    lines = result.stdout.splitlines()
    if result.returncode != 0 and result.stderr.strip():
        lines.append(f"journalctl: {result.stderr.strip()}")
    if not lines:
        return [f"No journal entries returned for user unit {unit_name}."]
    return select_log_lines(lines)


def get_service_status(service):
    healthy = check_health(service["healthUrl"])
    return {
        "name": service["name"],
        "healthy": healthy,
        "statusColor": "green" if healthy else "red",
        "logs": get_journal_logs(service["logUnit"]),
    }


class StatusHandler(BaseHTTPRequestHandler):
    def send_json(self, status_code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.split("?", 1)[0].rstrip("/") == "/status":
            self.send_json(200, [get_service_status(service) for service in SERVICES])
            return
        self.send_json(404, {"error": "not found"})

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format_string, *args):
        print(f"[status-poller] {self.address_string()} - {format_string % args}")


def main():
    server = ThreadingHTTPServer(("0.0.0.0", PORT), StatusHandler)
    print(f"Shade-brain status poller listening at http://localhost:{PORT}/status")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping status poller.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
