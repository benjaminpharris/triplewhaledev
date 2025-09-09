from snowflake.snowpark import Session
from snowflake.snowpark.functions import col, current_date, dateadd, lit, when
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Tuple
from config import SNOWFLAKE, CACHE_DIR, DAYS_BACK

def get_session():
    return Session.builder.configs(SNOWFLAKE).create()

def extract_orders(session: Session) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Extracts all initiated orders and splits them into two DataFrames:
    one for successful orders and one for cancellations/refunds.
    """
    t = session.table("DISH_RETAIL_DL.ORDER_ORCHESTRATION.CUSTOMERORDER_PARSE")

    # Define the canonical list of "successful" statuses, all lowercase.
    successful_statuses = ['complete', 'completed', 'inprogress', 'validated', 'activated']

    # 1. Broaden the query: REMOVE the ORDR_STATUS filter to get all initiated orders.
    #    The status column is converted to lowercase for consistent matching later.
    df_raw_pandas = t.filter(
        (col('ORDER_TYPE') == 'purchase') &
        (col('CHANNEL') == 'E-COMMERCE') &
        (col('BASETYPE').isin('PLAN', 'DEVICE')) &
        # The ORDR_STATUS filter is now removed from the SQL query.
        (col('OO_CREATEDDT_MT') >= dateadd('day', lit(-DAYS_BACK), current_date()))
    ).select(
        when(col('CHANNEL') == 'E-COMMERCE', 'www.boostmobile.com')
        .otherwise('offline')
        .alias('shop'),

        lit('USD').alias('currency'),

        col('ORDER_NBR').alias('order_id'),
        col('OO_CREATEDDT_MT').alias('created_at'),
        (col('MONTHLYTOTAL') + col('ITEM_COST')).alias('order_revenue'),
        col('subscriptionuuid').alias('customer_id'),
        col('BILLTOCONTACTEMAIL').alias('email'),
        col('BILLTOCONTACTPHONE').alias('customer_phone'),
        col('ORDER_ITEM_ID').alias('id'),
        col('BASETYPE').alias('product_name'),
        col('PRODUCT_NAME').alias('variant_name'),
        col('ITEM_LISTVALUE').alias('price'),
        col('QUANTITY').alias('quantity'),
        col('BUSINESSID').alias('variant_id'),
        col('SKU').alias('sku'),
        col('ORDR_STATUS') # We need this column for the split
    ).to_pandas()

    df_raw_pandas["extracted_at_utc"] = pd.Timestamp.utcnow()
    df_raw_pandas.columns = [c.lower() for c in df_raw_pandas.columns]

    # Ensure the status column exists and is lowercase for the split logic.
    if 'ordr_status' not in df_raw_pandas.columns:
        # If for some reason the column is missing, treat all as successful
        return df_raw_pandas, pd.DataFrame(columns=df_raw_pandas.columns)

    df_raw_pandas['ordr_status'] = df_raw_pandas['ordr_status'].str.lower()

    # 2. Perform the binary split in pandas.
    is_successful = df_raw_pandas['ordr_status'].isin(successful_statuses)
    
    df_successful = df_raw_pandas[is_successful].copy()
    df_cancellations = df_raw_pandas[~is_successful].copy()

    # 3. Return both DataFrames.
    return df_successful, df_cancellations


def cache_frame(df: pd.DataFrame, name_prefix="orders_line_items"):
    Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    path = f"{CACHE_DIR}/{name_prefix}_{ts}.parquet"
    df.to_parquet(path, index=False)
    return path
