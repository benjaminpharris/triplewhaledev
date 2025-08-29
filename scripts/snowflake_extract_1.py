from snowflake.snowpark import Session
from snowflake.snowpark.functions import col, current_date, dateadd, lit, when
import pandas as pd
from pathlib import Path
from datetime import datetime
from config import SNOWFLAKE, CACHE_DIR, DAYS_BACK

def get_session():
    return Session.builder.configs(SNOWFLAKE).create()

def extract_orders(session: Session) -> pd.DataFrame:

    t = session.table("DISH_RETAIL_DL.ORDER_ORCHESTRATION.CUSTOMERORDER_PARSE")

    df = t.filter(
        (col('ORDER_TYPE') == 'purchase') &
        (col('CHANNEL') == 'E-COMMERCE') &
        (col('BASETYPE').isin('PLAN', 'DEVICE')) &
        (col('ORDR_STATUS').isin('complete', 'inProgress')) &
        (col('OO_CREATEDDT_MT') >= dateadd('day', lit(-8), current_date()))
    ).select(
        when(col('CHANNEL') == 'E-COMMERCE', 'boostmobile.com')
        .otherwise('offline')
        .alias('shop'),

        lit('USD').alias('currency'),

        col('ORDER_NBR').alias('order_id'),
        col('OO_CREATEDDT_MT').alias('created_at'),
        col('MONTHLYTOTAL').alias('order_revenue'),
        col('subscriptionuuid').alias('customer_id'),
        col('BILLTOCONTACTEMAIL').alias('email'),
        col('BILLTOCONTACTPHONE').alias('customer_phone'),
        col('ORDER_ITEM_ID').alias('id'),
        col('BASETYPE').alias('product_name'),
        col('PRODUCT_NAME').alias('variant_name'),
        col('ITEM_LISTVALUE').alias('price'),
        col('QUANTITY').alias('quantity'),
        col('BUSINESSID').alias('variant_id'),
        col('SKU').alias('sku')
    ).to_pandas()

    df["extracted_at_utc"] = pd.Timestamp.utcnow()
    df.columns = [c.lower() for c in df.columns]
    return df

def cache_frame(df: pd.DataFrame, name_prefix="orders_line_items"):
    Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    path = f"{CACHE_DIR}/{name_prefix}_{ts}.parquet"
    df.to_parquet(path, index=False)
    return path
