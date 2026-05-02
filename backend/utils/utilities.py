import logging
import os

import httpx
from openai import AzureOpenAI
from supabase import ClientOptions, create_client
from supabase_auth import SyncMemoryStorage

from config import azure_endpoint, azure_key, azure_version, secKey, supabase_url
from datetime import datetime, timezone, timedelta
from dateutil import parser as dtparser

logger = logging.getLogger(__name__)


def _env_bool(key: str, default: bool) -> bool:
    raw = os.getenv(key)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


def _build_supabase_httpx_client() -> httpx.Client:
    """
    Shared httpx client for Supabase (PostgREST, storage, functions, auth).
    Defaults: HTTP/1.1 (http2=False) to reduce intermittent RemoteProtocolError
    on multiplexed HTTP/2 connections; capped pool for bursts.
    Override with SUPABASE_HTTP2=true if you prefer HTTP/2.
    """
    use_http2 = _env_bool("SUPABASE_HTTP2", default=False)
    connect_timeout = float(os.getenv("SUPABASE_HTTPX_CONNECT_TIMEOUT", "15"))
    read_timeout = float(os.getenv("SUPABASE_HTTPX_READ_TIMEOUT", "120"))
    max_connections = int(os.getenv("SUPABASE_HTTPX_MAX_CONNECTIONS", "20"))
    max_keepalive = int(os.getenv("SUPABASE_HTTPX_MAX_KEEPALIVE", "10"))
    timeout = httpx.Timeout(read_timeout, connect=connect_timeout)
    limits = httpx.Limits(
        max_connections=max_connections,
        max_keepalive_connections=max_keepalive,
    )
    logger.debug(
        "Supabase httpx client: http2=%s connect=%ss read=%ss max_conn=%s keepalive=%s",
        use_http2,
        connect_timeout,
        read_timeout,
        max_connections,
        max_keepalive,
    )
    return httpx.Client(
        timeout=timeout,
        limits=limits,
        http2=use_http2,
        follow_redirects=True,
    )


# ── Database client ────────────────────────────────────
_supabase_http = _build_supabase_httpx_client()
_supabase_opts = ClientOptions(
    storage=SyncMemoryStorage(),
    httpx_client=_supabase_http,
    postgrest_client_timeout=_supabase_http.timeout,
)
db = create_client(supabase_url, secKey, options=_supabase_opts)

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