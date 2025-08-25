import requests, time, csv, os, json
from pathlib import Path
from typing import Dict, Any, Iterable
from config import TW_API_KEY, TW_BASE, LOG_PATH, BATCH_SIZE, PAUSE_BETWEEN_REQ

HEADERS = {"x-api-key": TW_API_KEY, "Content-Type": "application/json"}

def _ensure_log():
    Path(os.path.dirname(LOG_PATH)).mkdir(parents=True, exist_ok=True)
    if not os.path.exists(LOG_PATH):
        with open(LOG_PATH, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["order_id","status","success","code","message"])  # header

def _load_done_ids() -> set[str]:
    if not os.path.exists(LOG_PATH): return set()
    done = set()
    with open(LOG_PATH, "r") as f:
        r = csv.DictReader(f)
        for row in r:
            if row.get("success","").lower() == "true":
                done.add(row.get("order_id",""))
    return done

def _append_log(order_id: str, status: str, success: bool, code: int|None, msg: str):
    with open(LOG_PATH, "a", newline="") as f:
        w = csv.writer(f)
        w.writerow([order_id, status, str(success), code or "", msg[:5000]])

def send_orders(payloads: Iterable[Dict[str, Any]], retry_failures: bool = True):
    _ensure_log()
    done_ids = _load_done_ids()

    url = f"{TW_BASE}/data-in/orders"
    sent, skipped, ok, fail = 0, 0, 0, 0

    batch = []
    for p in payloads:
        oid = p.get("order_id")
        if oid in done_ids:
            skipped += 1
            continue
        batch.append(p)
        if len(batch) >= BATCH_SIZE:
            s, o, f = _send_batch(url, batch, retry_failures)
            sent += s; ok += o; fail += f; batch = []
            time.sleep(PAUSE_BETWEEN_REQ)
    if batch:
        s, o, f = _send_batch(url, batch, retry_failures)
        sent += s; ok += o; fail += f

    return {"attempted": sent, "skipped": skipped, "ok": ok, "failed": fail}

def _send_batch(url: str, batch: list[Dict[str, Any]], retry_failures: bool):
    sent = ok = fail = 0
    for p in batch:
        oid = p.get("order_id")
        # basic validation guard
        if not oid or not p.get("created_at") or p.get("order_revenue") is None:
            _append_log(str(oid), "VALIDATION", False, None, "Missing required fields")
            fail += 1; continue

        tries, max_tries, backoff = 0, 5, 0.6
        while True:
            tries += 1
            try:
                r = requests.post(url, headers=HEADERS, data=json.dumps(p), timeout=30)
                code = r.status_code
                success = 200 <= code < 300
                if success:
                    _append_log(str(oid), "SENT", True, code, r.text)
                    ok += 1; sent += 1
                    break
                # retryable?
                if code in (408, 425, 429) or 500 <= code <= 599:
                    if tries < max_tries:
                        time.sleep(backoff); backoff *= 2; continue
                # hard failure
                _append_log(str(oid), "ERROR", False, code, r.text)
                fail += 1; sent += 1
                break
            except requests.RequestException as e:
                if tries < max_tries:
                    time.sleep(backoff); backoff *= 2; continue
                _append_log(str(oid), "EXCEPTION", False, None, str(e))
                fail += 1; sent += 1
                break
        time.sleep(PAUSE_BETWEEN_REQ)
    return sent, ok, fail
