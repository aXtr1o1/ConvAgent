from supabase import create_client
from openai import AzureOpenAI
from config import supabase_url, secKey, azure_endpoint, azure_key, azure_version
from datetime import datetime, timezone, timedelta
from dateutil import parser as dtparser

# ── Database client ────────────────────────────────────
db = create_client(supabase_url, secKey)

# ── OpenAI client ──────────────────────────────────────
openai_client = AzureOpenAI(
    api_key=azure_key,
    azure_endpoint=azure_endpoint,
    api_version=azure_version
)

# ── Timezone ───────────────────────────────────────────
IST = timezone(timedelta(hours=5, minutes=30))


def now_iso() -> str:
    """Current time in IST."""
    return datetime.now(IST).isoformat()


def to_ist(ts) -> str:
    """Convert any UTC or naive timestamp from Supabase to IST string."""
    if not ts:
        return ""
    try:
        dt = dtparser.parse(str(ts))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(IST).isoformat()
    except Exception:
        return str(ts)