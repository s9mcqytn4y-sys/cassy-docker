"""Virtual ESC/POS printer for automated tests (Sprint S0, PrdOpsAndPwaClose section 6).

Listens on TCP 9100 like a LAN thermal printer. Each connection is one print job:
the raw bytes are kept and a plain-text rendering is derived by stripping ESC/POS
control sequences. Tests read jobs over HTTP on port 9101:

  GET    /health          -> {"status": "ok"}
  GET    /jobs            -> [{"id", "bytes", "received_at", "text"}]
  GET    /jobs/<id>.bin   -> raw bytes
  DELETE /jobs            -> clears all jobs

Jobs live in memory only; the sink is a test fixture, not a print server.
"""

import json
import re
import socketserver
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

JOBS = []
LOCK = threading.Lock()
MAX_JOB_BYTES = 1 << 20

# ESC/GS commands with fixed argument counts; anything else is dropped byte by byte.
_ESC_ARGS = {b"@": 0, b"!": 1, b"E": 1, b"-": 1, b"a": 1, b"d": 1, b"p": 3, b"t": 1, b"2": 0, b"3": 1, b"M": 1, b"G": 1}
_GS_ARGS = {b"!": 1, b"V": 1, b"B": 1, b"h": 1, b"w": 1, b"H": 1, b"f": 1, b"k": 1}


def render_text(data: bytes) -> str:
    """Strip ESC/POS commands and return printable text (CP437/latin-1 safe)."""
    out = bytearray()
    i = 0
    while i < len(data):
        b = data[i]
        if b in (0x1B, 0x1D) and i + 1 < len(data):
            table = _ESC_ARGS if b == 0x1B else _GS_ARGS
            cmd = data[i + 1:i + 2]
            if b == 0x1D and cmd == b"V" and i + 2 < len(data) and data[i + 2] in (65, 66):
                i += 4  # GS V m n (partial cut with feed)
                continue
            if b == 0x1D and cmd == b"v":  # GS v 0 raster image: skip header + payload
                if i + 7 < len(data):
                    w = data[i + 4] | (data[i + 5] << 8)
                    h = data[i + 6] | (data[i + 7] << 8)
                    i += 8 + w * h
                    continue
            i += 2 + table.get(cmd, 0)
            continue
        if b in (0x0A, 0x0D) or 0x20 <= b < 0x7F:
            out.append(b)
        i += 1
    return re.sub(r"\r\n?", "\n", out.decode("latin-1"))


class PrinterHandler(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.settimeout(5)
        chunks, size = [], 0
        try:
            while size < MAX_JOB_BYTES:
                chunk = self.request.recv(65536)
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
        except OSError:
            pass  # client closed or idle timeout ends the job
        data = b"".join(chunks)
        if not data:
            return
        with LOCK:
            JOBS.append({
                "id": len(JOBS) + 1,
                "bytes": len(data),
                "received_at": datetime.now(timezone.utc).isoformat(),
                "text": render_text(data),
                "raw": data,
            })


class ApiHandler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        payload = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path == "/health":
            return self._send(200, {"status": "ok"})
        with LOCK:
            if self.path == "/jobs":
                return self._send(200, [{k: v for k, v in j.items() if k != "raw"} for j in JOBS])
            m = re.fullmatch(r"/jobs/(\d+)\.bin", self.path)
            if m and 0 < int(m.group(1)) <= len(JOBS):
                return self._send(200, JOBS[int(m.group(1)) - 1]["raw"], "application/octet-stream")
        self._send(404, {"error": "not_found"})

    def do_DELETE(self):
        if self.path != "/jobs":
            return self._send(404, {"error": "not_found"})
        with LOCK:
            JOBS.clear()
        self._send(200, {"cleared": True})

    def log_message(self, *_):
        pass


def _self_check():
    sample = b"\x1b@\x1ba\x01CASSY\n\x1d!\x11Rp 25.000\n\x1dVA\x00"
    assert render_text(sample) == "CASSY\nRp 25.000\n", render_text(sample)


if __name__ == "__main__":
    _self_check()
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    printer = socketserver.ThreadingTCPServer(("0.0.0.0", 9100), PrinterHandler)
    threading.Thread(target=printer.serve_forever, daemon=True).start()
    print("escpos-sink: printer :9100, api :9101", flush=True)
    ThreadingHTTPServer(("0.0.0.0", 9101), ApiHandler).serve_forever()
