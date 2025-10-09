# Triple Whale Order Ingest (Snowflake → TW Data-In)

## What this does (plain English)

### Locally
- Pulls previous 8 days e-comm orders + line items from Snowflake (read-only via Snowpark).
  - `DISH_RETAIL_DL.ORDER_ORCHESTRATION.CUSTOMERORDER_PARSE`
- Cleans/validates fields (email, currency, timestamps).
- Groups line items by `order_id` into ONE payload per order (prevents revenue double-count).
  - Creates a separate set of sub-items for incomplete orderers tagged as *refunds* 

### In Google Collab (or another cloud notebook service)
> Currently at *https://colab.research.google.com/drive/1vNnclUTEUt-SlU81cAeCB9FahVFDMEhH#scrollTo=XpjeaGOAwPhE*
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

### Data Dictionary:
> https://docs.google.com/spreadsheets/d/1dfz5_InxLi96-dBxHJzOODV_T_XzBGDPuqzqqKDpQ18/edit?gid=1808364879#gid=1808364879

## Data sources (Snowflake)
- Table: `DISH_RETAIL_DL.ORDER_ORCHESTRATION.CUSTOMERORDER_PARSE`
- Filter: e-comm only, `BASETYPE in ('PLAN','DEVICE')`, status in (`complete`,`inProgress`), last `DAYS_BACK` by `OO_CREATEDDT_MT` (Mountain Time)


# Quick start Guide

Here's the steps you need to take after cloning the repository to run and test the code

```bash
# 1) create env & install
conda env create -f environment.yml 

# 2) copy and edit env - these contain the connection parameters and login information nedded 
cp .env.example .env
# fill in TW_API_KEY and SNOWFLAKE_USER
```

## Folder Structure

1. Create a synced Google Drive folder locally
2. Point the dataframe created by validate_rowwise() _second to last block in Master.ipynb_ to save to that folder
3. Connect that folder to the Google Collab notebook and point the _val_successes_ and _val_cancellations_ to the success and cancellations parquet files

---

# Code Contents

This repository modularizes the data extraction, processing, and upload steps necessary to provide core data to TripleWhale's platform.

1. **Master.ipynb** - The main script that calls submodules. Each submodule performs a specific function in the data processing pipeline
2.  *snowflake_extract_1* - Calls "DISH_RETAIL_DL.ORDER_ORCHESTRATION.CUSTOMERORDER_PARSE" to gather orders tracked in Snowflake
3.  *normalize_2* - Sanitizes fields from the orders table
4.  *group_payloads_3* - Collapses order data on order ID. This means each row is one order id 
5.**-In Google Collab-**  *send_triplewhale_4* - Sends data to the Triplewhale API and captures logs in case of upload failure
