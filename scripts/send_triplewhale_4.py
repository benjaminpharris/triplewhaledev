import requests, time, csv, os, json
from pathlib import Path
from typing import Dict, Any

# --- Configuration is imported from your config.py file ---
from config import TW_API_KEY, TW_BASE, LOG_PATH

# --- Global Headers ---
HEADERS = {"x-api-key": TW_API_KEY, "Content-Type": "application/json"}


# --- New Function to Handle Refund Payloads ---
def send_refunds_from_dataframe(payloads: list[Dict[str, Any]], batch_size: int = 100, pause_between_req: float = 0.6, retry_failures: bool = True):
    """
    Sends refund enrichment payloads to the Triple Whale Data-In API.
    """
    _ensure_log()
    done_ids = _load_done_ids("REFUND") # Use a specific status to track refunds
    
    # The endpoint for enriching orders is different from creating new ones.
    url = f"{TW_BASE}/data-in/enrich/orders"
    
    sent, skipped, ok, fail = 0, 0, 0, 0

    batch = []
    for p in payloads:
        oid = p.get("order_id")
        if oid in done_ids:
            skipped += 1
            continue
        batch.append(p)
        if len(batch) >= batch_size:
            s, o, f = _send_batch(url, batch, "REFUND", pause_between_req, retry_failures)
            sent += s; ok += o; fail += f; batch = []
            time.sleep(pause_between_req)
    if batch:
        s, o, f = _send_batch(url, batch, "REFUND", pause_between_req, retry_failures)
        sent += s; ok += o; fail += f

    return {"attempted": sent, "skipped": skipped, "ok": ok, "failed": fail}


# --- Existing Function for New Order Payloads (Unchanged) ---
def send_orders_from_dataframe(payloads: list[Dict[str, Any]], batch_size: int = 100, pause_between_req: float = 0.6, retry_failures: bool = True):
    """
    Sends new order payloads to the Triple Whale Data-In API.
    """
    _ensure_log()
    done_ids = _load_done_ids("SENT")
    
    url = f"{TW_BASE}/data-in/orders"
    sent, skipped, ok, fail = 0, 0, 0, 0

    batch = []
    for p in payloads:
        oid = p.get("order_id")
        if oid in done_ids:
            skipped += 1
            continue
        batch.append(p)
        if len(batch) >= batch_size:
            s, o, f = _send_batch(url, batch, "SENT", pause_between_req, retry_failures)
            sent += s; ok += o; fail += f; batch = []
            time.sleep(pause_between_req)
    if batch:
        s, o, f = _send_batch(url, batch, "SENT", pause_between_req, retry_failures)
        sent += s; ok += o; fail += f

    return {"attempted": sent, "skipped": skipped, "ok": ok, "failed": fail}


# --- Internal Helper Functions (with minor adjustments for reuse) ---

def _send_batch(url: str, batch: list[Dict[str, Any]], success_log_status: str, pause_between_req: float, retry_failures: bool):
    sent = ok = fail = 0
    for p in batch:
        oid = p.get("order_id")
        
        # Validation guard now checks for payload type (order vs refund)
        is_refund = "refunds" in p
        is_valid = True
        if is_refund:
            if not oid or not p.get("refunds"):
                is_valid = False
        else: # Is a new order
            if not oid or not p.get("created_at") or p.get("order_revenue") is None:
                is_valid = False

        if not is_valid:
            _append_log(str(oid), "VALIDATION", False, None, "Missing required fields for payload type")
            fail += 1
            print(f"Order {oid}: VALIDATION FAILED - Missing required fields")
            continue

        tries, max_tries, backoff = 0, 5, 0.6
        while True:
            tries += 1
            try:
                r = requests.post(url, headers=HEADERS, data=json.dumps(p), timeout=30)
                code = r.status_code
                success = 200 <= code < 300
                if success:
                    _append_log(str(oid), success_log_status, True, code, r.text)
                    ok += 1; sent += 1
                    print(f"Order {oid}: SUCCESS ({success_log_status}, Code: {code})")
                    break
                
                print(f"Order {oid}: FAILED (Code: {code})")
                print(f"Request Payload: {json.dumps(p)}")
                print(f"Response Body: {r.text}")

                if code in (408, 425, 429) or 500 <= code <= 599:
                    if tries < max_tries and retry_failures:
                        time.sleep(backoff); backoff *= 2; continue

                _append_log(str(oid), "ERROR", False, code, r.text)
                fail += 1; sent += 1
                break
            except requests.RequestException as e:
                if tries < max_tries and retry_failures:
                    time.sleep(backoff); backoff *= 2; continue
                _append_log(str(oid), "EXCEPTION", False, None, str(e))
                fail += 1; sent += 1
                print(f"Order {oid}: EXCEPTION - {e}")
                break
        time.sleep(pause_between_req)
    return sent, ok, fail

def _ensure_log():
    Path(os.path.dirname(LOG_PATH)).mkdir(parents=True, exist_ok=True)
    if not os.path.exists(LOG_PATH):
        with open(LOG_PATH, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["order_id", "status", "success", "code", "message"])

def _load_done_ids(status_to_check: str) -> set[str]:
    if not os.path.exists(LOG_PATH): return set()
    done = set()
    with open(LOG_PATH, "r") as f:
        r = csv.DictReader(f)
        for row in r:
            if row.get("success", "").lower() == "true" and row.get("status") == status_to_check:
                done.add(row.get("order_id", ""))
    return done

def _append_log(order_id: str, status: str, success: bool, code: int|None, msg: str):
    with open(LOG_PATH, "a", newline="") as f:
        w = csv.writer(f)
        w.writerow([order_id, status, str(success), code or "", msg[:5000]])
