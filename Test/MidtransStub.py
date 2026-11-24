"""Fake Midtrans Core API for the automated test stack (S4-Q8, PrdOpsAndPwaClose section 12).

The API under test points its Midtrans calls here (MIDTRANS_API_BASE_URL). Charges stay
"pending" until a test settles them; settling posts a webhook signed exactly like Midtrans:
SHA-512(order_id + status_code + gross_amount + server_key), with the server key the charge
was made with (HTTP Basic user), so store (BYOK) and default keys both verify.

  POST /v2/charge                      -> Midtrans-shaped pending charge (qris, gopay, shopeepay, bank_transfer)
  GET  /v2/<order_id>/status           -> current state of that charge
  GET  /_stub/health                   -> {"status": "ok"}
  GET  /_stub/charges                  -> every charge, newest first (no server keys)
  POST /_stub/charges/<order_id>/settle -> {"transaction_status": "settlement"|"expire"|"deny"|"cancel",
                                           "webhook_url": optional} ; returns the webhook HTTP status

Charges live in memory only; never point a real store at this.
"""

import base64
import hashlib
import json
import os
import threading
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "http://api:8080/api/v1/payments/midtrans/webhook")
CHARGES = {}
LOCK = threading.Lock()
STATUS_CODES = {"pending": "201", "settlement": "200", "capture": "200", "expire": "407", "deny": "202", "cancel": "200"}


def now_wib() -> datetime:
    return datetime.now(timezone(timedelta(hours=7)))


def stamp(t: datetime) -> str:
    return t.strftime("%Y-%m-%d %H:%M:%S")


def public(charge: dict) -> dict:
    return {k: v for k, v in charge.items() if not k.startswith("_")}


def new_charge(body: dict, server_key: str, override_url: str) -> dict:
    details = body.get("transaction_details") or {}
    order_id = str(details.get("order_id", ""))
    gross = int(details.get("gross_amount", 0))
    payment_type = body.get("payment_type", "")
    created = now_wib()
    tx_id = str(uuid.uuid4())
    charge = {
        "status_code": "201",
        "status_message": "Success, transaction is created",
        "transaction_id": tx_id,
        "order_id": order_id,
        "merchant_id": "G000000000",
        "gross_amount": f"{gross}.00",
        "currency": "IDR",
        "payment_type": payment_type,
        "transaction_time": stamp(created),
        "transaction_status": "pending",
        "fraud_status": "accept",
        "expiry_time": stamp(created + timedelta(minutes=15)),
        "_server_key": server_key,
        "_webhook_url": override_url,
    }
    if payment_type == "qris":
        charge["acquirer"] = (body.get("qris") or {}).get("acquirer", "gopay")
        charge["qr_string"] = "00020101021226620014COM.STUB.TEST" + order_id[:20] + "5204581253033605802ID6304ABCD"
        charge["actions"] = [{"name": "generate-qr-code", "method": "GET", "url": f"http://midtrans-stub/qr/{tx_id}"}]
    elif payment_type in ("gopay", "shopeepay"):
        charge["actions"] = [
            {"name": "deeplink-redirect", "method": "GET", "url": f"https://stub.invalid/{payment_type}/{tx_id}"},
        ]
    elif payment_type == "bank_transfer":
        bank = (body.get("bank_transfer") or {}).get("bank", "bca")
        va = "8808" + str(abs(hash(order_id)) % 10**10).zfill(10)
        if bank == "permata":
            charge["permata_va_number"] = va
        else:
            charge["va_numbers"] = [{"bank": bank, "va_number": va}]
    return charge


def signed_notification(charge: dict) -> dict:
    status_code = STATUS_CODES.get(charge["transaction_status"], "200")
    raw = charge["order_id"] + status_code + charge["gross_amount"] + charge["_server_key"]
    note = public(charge)
    note["status_code"] = status_code
    note["signature_key"] = hashlib.sha512(raw.encode()).hexdigest()
    return note


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body) -> None:
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(length) or b"{}")

    def _server_key(self) -> str:
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Basic "):
            return ""
        return base64.b64decode(auth[6:]).decode().split(":", 1)[0]

    def do_GET(self) -> None:
        parts = self.path.strip("/").split("/")
        if self.path == "/_stub/health":
            return self._send(200, {"status": "ok"})
        if self.path == "/_stub/charges":
            with LOCK:
                charges = [public(c) for c in reversed(list(CHARGES.values()))]
            return self._send(200, charges)
        if len(parts) == 3 and parts[0] == "v2" and parts[2] == "status":
            with LOCK:
                charge = CHARGES.get(parts[1])
            if charge is None:
                return self._send(404, {"status_code": "404", "status_message": "Transaction doesn't exist."})
            out = public(charge)
            out["status_code"] = STATUS_CODES.get(charge["transaction_status"], "200")
            return self._send(200, out)
        self._send(404, {"status_code": "404", "status_message": "not found"})

    def do_POST(self) -> None:
        parts = self.path.strip("/").split("/")
        if self.path == "/v2/charge":
            key = self._server_key()
            if not key:
                return self._send(401, {"status_code": "401", "status_message": "Unknown Merchant server_key/id"})
            charge = new_charge(self._body(), key, self.headers.get("X-Override-Notification", ""))
            with LOCK:
                existing = CHARGES.get(charge["order_id"])
                if existing is None:
                    CHARGES[charge["order_id"]] = charge
                else:
                    charge = existing  # same order_id again: Midtrans answers with the original charge
            return self._send(200, public(charge))
        if len(parts) == 4 and parts[:2] == ["_stub", "charges"] and parts[3] == "settle":
            body = self._body()
            with LOCK:
                charge = CHARGES.get(parts[2])
                if charge is not None:
                    charge["transaction_status"] = body.get("transaction_status", "settlement")
                    charge["settlement_time"] = stamp(now_wib())
                    note = signed_notification(charge)
            if charge is None:
                return self._send(404, {"error": "unknown order_id"})
            target = body.get("webhook_url") or charge["_webhook_url"] or WEBHOOK_URL
            req = urllib.request.Request(target, data=json.dumps(note).encode(), method="POST",
                                         headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=10) as res:
                    return self._send(200, {"webhook_status": res.status, "webhook_body": res.read().decode()})
            except urllib.error.HTTPError as err:
                return self._send(200, {"webhook_status": err.code, "webhook_body": err.read().decode()})
        self._send(404, {"error": "not found"})

    def log_message(self, fmt, *args) -> None:
        print("midtrans-stub", fmt % args, flush=True)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 9200), Handler).serve_forever()
