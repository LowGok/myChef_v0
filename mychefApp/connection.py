import streamlit as st
import cloudinary
import time
import functools
import os
from sqlalchemy.exc import DBAPIError


def genai_http_options():
    options = {"timeout": 120000, "retry_options": {
        "attempts": 2, "http_status_codes": [503], "initial_delay": 1, "max_delay": 2,
    }}
    if os.environ.get("MYCHEF_E2E_IPV4") == "1":
        import httpx
        options["client_args"] = {"transport": httpx.HTTPTransport(local_address="0.0.0.0")}
    return options

def init_connection():
    """
    Initializes and returns a SQLConnection to Neon PostgreSQL
    configured with connection pre-ping, recycling, and TCP keepalives.
    """
    return st.connection(
        'neon',
        type='sql',
        pool_pre_ping=True,
        pool_recycle=180,
        connect_args={
            "connect_timeout": 10,
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5
        }
    )

def reset_connection():
    """Reset the same configured connection used by database operations."""
    init_connection().reset()


def is_transient_db_error(exc: Exception) -> bool:
    """Recognize invalidated DBAPI connections, not arbitrary application errors."""
    if not isinstance(exc, DBAPIError):
        return False
    if exc.connection_invalidated:
        return True
    sqlstate = getattr(exc.orig, "sqlstate", None) or getattr(exc.orig, "pgcode", None)
    return bool(sqlstate and sqlstate.startswith("08"))


def with_db_retry(max_retries: int = 3, initial_delay: float = 1.0,
                  backoff_factor: float = 2.0, *, read_only: bool = False):
    """Retry explicitly read-only work; never replay writes after a lost response.

    max_retries is the maximum number of attempts, including the first call.
    Database errors return None for existing UI callers. Programming errors propagate.
    """
    if max_retries < 1 or initial_delay < 0 or backoff_factor < 1:
        raise ValueError("Invalid database retry settings")

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            attempts = max_retries if read_only else 1
            for attempt in range(attempts):
                try:
                    return func(*args, **kwargs)
                except DBAPIError as exc:
                    transient = is_transient_db_error(exc)
                    if transient:
                        reset_connection()
                    if transient and attempt + 1 < attempts:
                        time.sleep(delay)
                        delay *= backoff_factor
                        continue
                    # SQLAlchemy exception text can contain passwords and other parameters.
                    st.error("The database operation could not be confirmed. Refresh before trying again.")
                    return None
        return wrapper
    return decorator

@st.cache_resource()
def configure_cloudinary():
    cloudinary.config(
        cloud_name = st.secrets["cloudinary"]["cloudinary_cloud_name"],
        api_key = st.secrets["cloudinary"]["cloudinary_api_key"],
        api_secret = st.secrets["cloudinary"]["cloudinary_api_secret"]
    )
