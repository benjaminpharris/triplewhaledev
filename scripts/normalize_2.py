import pandas as pd
import re, numpy as np
from zoneinfo import ZoneInfo
from config import TIMEZONE_LOCAL # This is still used for timezone conversion

# Unchanged from your original script
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
REQUIRED_FOR_ORDER = ["order_id", "created_at_utc", "order_revenue"]
REQUIRED_CUSTOMER_ANY = ["customer_id", "email"]

# Unchanged from your original script
def clean_email(x: str) -> str | None:
    if pd.isna(x): return None
    x = str(x).strip().lower()
    return x if EMAIL_RE.match(x or "") else None

# Renamed for clarity, but logic is the same and still works correctly
def to_iso_utc(s: pd.Series) -> pd.Series:
    """
    Input: pandas Series with datetimes (e.g., from Snowflake's to_pandas).
    Output: ISO-8601 UTC strings formatted with a Z.
    """
    def conv(v):
        if pd.isna(v) or v == "": return np.nan
        try:
            # pd.to_datetime handles various inputs, including objects from the DB
            dt = pd.to_datetime(v)
            # If the datetime object from Snowflake is "naive" (no timezone info),
            # assume it's in our local timezone.
            if dt.tzinfo is None:
                dt = dt.tz_localize(ZoneInfo(TIMEZONE_LOCAL))
            # Convert to UTC and format as a standard string
            return dt.tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            return np.nan
    return s.apply(conv)

def normalize(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans and standardizes columns provided by the Snowflake extract.
    """
    out = df.copy()

    # Emails: still need cleaning and validation
    out["email"] = out.get("email", pd.Series([None]*len(out))).apply(clean_email)

    # Revenue: still good practice to ensure it's a numeric type
    out["order_revenue"] = pd.to_numeric(out.get("order_revenue", pd.Series([None]*len(out))), errors="coerce")

    # Timestamps: convert to the standard UTC ISO Z format
    out["created_at_utc"] = to_iso_utc(out.get("created_at", pd.Series([None]*len(out))))

    return out

# This function requires no changes! Its logic was correct, but the data was missing before.
def validate_rowwise(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds validation columns and drops fully invalid rows.
    Accept: (customer_id OR email) AND required order fields.
    """
    out = df.copy()
    out["has_min_customer"] = (~out.get("customer_id", pd.Series([np.nan]*len(out))).isna()) | (~out.get("email", pd.Series([np.nan]*len(out))).isna())
    for c in REQUIRED_FOR_ORDER:
        out[f"has_{c}"] = ~out.get(c, pd.Series([np.nan]*len(out))).isna()
    needed_flags = [f"has_{c}" for c in REQUIRED_FOR_ORDER] + ["has_min_customer"]
    out["is_valid"] = out[needed_flags].all(axis=1)
    return out