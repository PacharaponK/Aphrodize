"""Synthetic API/Discord receiver for the isolated Docker smoke check."""

import json
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

fault = False
notifications = []


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_GET(self):
        global fault
        if self.path == "/fault":
            fault = True
        elif self.path == "/recover":
            fault = False
        if self.path == "/notifications":
            payload = json.dumps(notifications)
        elif self.path == "/api/v1/monitoring/metrics":
            payload = (
                'aphrodize_dependency_up{dependency="redis"} ' + str(int(not fault)) + "\n"
                'aphrodize_dependency_required{dependency="redis"} 1\n'
                "aphrodize_collector_success 1\n"
                f"aphrodize_collector_timestamp_seconds {time.time()}\n"
                "aphrodize_uv_monitoring_enabled 0\n"
                "aphrodize_uv_forecast_ready 0\n"
                "aphrodize_uv_quality_ready 0\n"
            )
        else:
            payload = '{"status":"ok"}'
        self.send_response(200)
        self.send_header(
            "Content-Type",
            "text/plain; version=0.0.4"
            if self.path == "/api/v1/monitoring/metrics"
            else "application/json",
        )
        self.end_headers()
        self.wfile.write(payload.encode())
        print(
            json.dumps(
                {
                    "event": "smoke_probe",
                    "request_id": "d" * 32,
                    "message": "PRIVATE_SENTINEL",
                    "password": "PRIVATE_SENTINEL",
                },
                separators=(",", ":"),
            ),
            flush=True,
        )

    def do_POST(self):
        data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        notifications.append(data)
        self.send_response(204)
        self.end_headers()


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
