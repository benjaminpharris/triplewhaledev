# Triple Whale Order Ingest (Snowflake → TW Data-In)

## What this does (plain English)
- Pulls recent e-comm orders + line items from Snowflake (read-only via Snowpark).
- Cleans/validates fields (email, currency, timestamps).
- Groups line items by `order_id` into ONE payload per order (prevents revenue double-count).
- Optionally **dry-runs** to inspect payloads without sending.
- Sends orders to Triple Whale’s Data-In **Create Order Record** endpoint with retries.
- Logs successes/failures to a CSV for idempotent re-runs.

## Data we send to Triple Whale (per order)
- `customer`: `{ id (subscriptionuuid), email, phone }` (email optional if id present)
- `shop`: `boostmobile.com` (or your override)
- `order_id`: platform order id
- `created_at`: UTC ISO-8601 (e.g., `2025-08-20T23:22:01Z`)
- `currency`: `USD`
- `order_revenue`: numeric (order-level)
- `line_items[]`: each with `{ id, product_name, variant_name, price, quantity, variant_id, sku }`

## Data sources (Snowflake)
- Table: `DISH_RETAIL_DL.ORDER_ORCHESTRATION.CUSTOMERORDER_PARSE`
- Filter: e-comm only, `BASETYPE in ('PLAN','DEVICE')`, status in (`complete`,`inProgress`), last `DAYS_BACK` by `OO_CREATEDDT_MT` (Mountain Time)

## Project layout

---


# Quick start Guide

Here's the steps you need to take after cloning the repository to run and test the code

```bash
# 1) create env & install
conda env create -f environment.yml 

# 2) copy and edit env - these contain the connection parameters and login information nedded 
cp .env.example .env
# fill in TW_API_KEY and SNOWFLAKE_USER

# 3) run a dry-run (no API calls)
DRY_RUN=true python -m tw_ingest.run_daily

# 4) inspect outputs
ls ./data/cache/     # parquet extracts
cat logs/tw_order_upload_log.csv
```

---

# Code Contents

This repository modularizes the data extraction, processing, and upload steps necessary to provide core data to TripleWhale's platform.

1. **daily_send.py** - The main script that calls submodules automatically via Github Actions
2. 