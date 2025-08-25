import pandas as pd
from extract_snowflake import get_session, extract_orders, cache_frame
from normalize import normalize, validate_rowwise
from group_payloads import rows_to_payloads
from send_triplewhale import send_orders

def main():
    session = get_session()
    raw = extract_orders(session)
    cache_path = cache_frame(raw, "orders_line_items")

    norm = normalize(raw)
    val = validate_rowwise(norm)

    payloads = rows_to_payloads(val)
    metrics = send_orders(payloads, retry_failures=True)
    print("CACHE:", cache_path)
    print("RESULT:", metrics)

if __name__ == "__main__":
    main()
