import os

from dotenv import load_dotenv
load_dotenv()

# --- Secrets (set in GitHub Actions + local .env) ---
TW_API_KEY = os.getenv("TW_API_KEY")  # required
TW_BASE = os.getenv("TW_BASE", "https://api.triplewhale.com/api/v2")

# --- Data assumptions ---
SHOP_OVERRIDE = os.getenv("SHOP_OVERRIDE")  # e.g., "boostmobile.com" or leave None
DEFAULT_CURRENCY = os.getenv("DEFAULT_CURRENCY", "USD")

# --- Time / windows ---
TIMEZONE_LOCAL = os.getenv("TIMEZONE_LOCAL", "America/Denver")  # input tz
DAYS_BACK = int(os.getenv("DAYS_BACK", "8"))  # match your SQL window

# --- Logging / caching ---
CACHE_DIR = os.getenv("CACHE_DIR", "./cache")
LOG_PATH = os.getenv("LOG_PATH", "./logs/tw_order_upload_log.csv")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "500"))
PAUSE_BETWEEN_REQ = float(os.getenv("PAUSE_BETWEEN_REQ", "0.2"))

# --- Snowflake (read-only Snowpark) ---
SNOWFLAKE = {
    "account": os.getenv("SNOWFLAKE_ACCOUNT", "yva20138.us-west-2.privatelink"),
    "user": os.getenv("SNOWFLAKE_USER"),
    "authenticator": os.getenv("SNOWFLAKE_AUTH", "externalbrowser"),
    "insecure_mode": os.getenv("SNOWFLAKE_INSECURE", "true").lower() == "true",
    # role / warehouse / db / schema are optional for your Snowpark query style
}
