import pandas as pd
from typing import Dict, Any, List, Iterable

def rows_to_payloads(df_valid: pd.DataFrame) -> list[Dict[str, Any]]:
    """
    Collapse line-items to one order payload per order_id with line_items[].
    Assumes df_valid['is_valid'] is True for rows we keep.
    """
    keep = df_valid[df_valid["is_valid"]].copy()

    # one order per order_id (line_items aggregated)
    payloads: List[Dict[str, Any]] = []
    for order_id, g in keep.groupby("order_id"):
        g = g.sort_values("id")  # stable

        # build line items
        items = []
        for _, r in g.iterrows():
            items.append({
                "id": str(r.get("id")),
                "product_name": str(r.get("product_name") or ""),
                "variant_name": str(r.get("variant_name") or ""),
                "price": float(r.get("price") or 0.0),
                "quantity": int(r.get("quantity") or 1),
                "variant_id": str(r.get("variant_id") or ""),
                "sku": str(r.get("sku") or ""),
            })

        # take order-level fields from first row
        r0 = g.iloc[0]
        payloads.append({
            "customer": {
                # TW accepts id and/or email—send both when available
                "id": str(r0.get("customer_id")) if pd.notna(r0.get("customer_id")) else None,
                "email": r0.get("email") if pd.notna(r0.get("email")) else None,
                "phone": r0.get("customer_phone") if pd.notna(r0.get("customer_phone")) else None,
            },
            "shop": r0.get("shop"),
            "order_id": str(order_id),
            "created_at": r0.get("created_at_utc"),
            "currency": r0.get("currency"),
            "order_revenue": float(r0.get("order_revenue") or 0.0),
            "line_items": items,
        })
    return payloads