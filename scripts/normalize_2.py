import pandas as pd
import re, numpy as np
from zoneinfo import ZoneInfo
from config import TIMEZONE_LOCAL, DEFAULT_CURRENCY, SHOP_OVERRIDE

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")

REQUIRED_FOR_ORDER = ["order_id", "created_at_utc", "order_revenue"]
REQUIRED_CUSTOMER_ANY = ["customer_id", "email"]  # accept either

def clean_email(x: str) -> str | None:
    if pd.isna(x): return None
    x = str(x).strip().lower()
    return x if EMAIL_RE.match(x or "") else None

def to_iso_utc_from_local(s: pd.Series) -> pd.Series:
    # input: local time strings (America/Denver), output: ISO-8601 Z
    def conv(v):
        if pd.isna(v) or v == "": return np.nan
        try:
            dt = pd.to_datetime(v)
            if dt.tzinfo is None:
                dt = dt.tz_localize(ZoneInfo(TIMEZONE_LOCAL))
            else:
                dt = dt.tz_convert(ZoneInfo(TIMEZONE_LOCAL))
            return dt.tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            return np.nan
    return s.apply(conv)

def normalize(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    # shop domain
    out["shop"] = SHOP_OVERRIDE if SHOP_OVERRIDE else "boostmobile.com"

    # emails
    out["email"] = out.get("email", pd.Series([None]*len(out))).apply(clean_email)

    # revenue numeric
    out["order_revenue"] = pd.to_numeric(out.get("order_revenue"), errors="coerce")

    # currency
    out["currency"] = DEFAULT_CURRENCY

    # created_at: local → UTC ISO Z
    out["created_at_utc"] = to_iso_utc_from_local(out.get("created_at_local"))

    return out

def validate_rowwise(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds validation columns and drops fully invalid rows.
    Accept: (customer_id OR email) AND required order fields.
    """
    out = df.copy()
    out["has_min_customer"] = (~out.get("customer_id").isna()) | (~out.get("email").isna())
    for c in REQUIRED_FOR_ORDER:
        out[f"has_{c}"] = ~out.get(c).isna()
    needed_flags = [f"has_{c}" for c in REQUIRED_FOR_ORDER] + ["has_min_customer"]
    out["is_valid"] = out[needed_flags].all(axis=1)
    return out
