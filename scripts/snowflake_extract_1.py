from snowflake.snowpark import Session
from snowflake.snowpark.functions import col, current_date, dateadd
import pandas as pd
from pathlib import Path
from datetime import datetime
from config import SNOWFLAKE, CACHE_DIR, DAYS_BACK

def get_session():
    return Session.builder.configs(SNOWFLAKE).create()

def extract_orders(session: Session) -> pd.DataFrame:
    """
    Mirrors your SQL: returns one row per line item with order-level columns repeated.
    Filter to last N days by Mountain Time creation date in the source table.
    """
    t = session.table("DISH_RETAIL_DL.ORDER_ORCHESTRATION.CUSTOMERORDER_PARSE")

    # Example of filtering: adapt to your exact columns/filters from the SQL you sent
    df = (
        t.filter((col("channel") == "ecomm") & col("BASETYPE").isin("PLAN", "DEVICE"))
         .filter(col("ORDERSTATUS").isin("complete", "inProgress"))
         .filter(col("OO_CREATEDDT_MT") >= dateadd("day", -DAYS_BACK, current_date()))
         .select(
             col("subscriptionuuid").alias("customer_id"),
             col("email"),
             col("customer_phone"),
             col("OO_CREATEDDT_MT").alias("created_at_local"),
             col("ORDER_ID").alias("order_id"),
             col("MONTHLYTOTAL").alias("order_revenue"),
             # Line-item fields:
             col("ORDER_ITEM_ID").alias("id"),
             col("BASETYPE").alias("product_name"),
             col("PRODUCT_NAME").alias("variant_name"),
             col("ITEM_LISTVALUE").alias("price"),
             col("QUANTITY").alias("quantity"),
             col("BUSINESSID").alias("variant_id"),
             col("SKU").alias("sku"),
         )
    ).to_pandas()  # safe: read-only pull

    df["extracted_at_utc"] = pd.Timestamp.utcnow()
    return df

def cache_frame(df: pd.DataFrame, name_prefix="orders_line_items"):
    Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    path = f"{CACHE_DIR}/{name_prefix}_{ts}.parquet"
    df.to_parquet(path, index=False)
    return path
