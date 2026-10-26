import streamlit as st
import cloudinary
import time
import functools
from sqlalchemy.exc import OperationalError, InterfaceError, DBAPIError

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
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5
        }
    )

def reset_connection():
    """Resets the cached database connection so a fresh pool is created."""
    try:
        conn = st.connection('neon', type='sql')
        conn.reset()
    except Exception:
        pass

def is_transient_db_error(exc: Exception) -> bool:
    """Detects whether an exception is a transient disconnect/SSL failure."""
    if isinstance(exc, (OperationalError, InterfaceError)):
        return True
    if isinstance(exc, DBAPIError) and exc.connection_invalidated:
        return True
    msg = str(exc).lower()
    transient_indicators = [
        "ssl syscall error",
        "eof detected",
        "connection already closed",
        "server closed the connection",
        "connection reset by peer",
        "could not connect to server",
        "broken pipe"
    ]
    return any(indicator in msg for indicator in transient_indicators)

def with_db_retry(max_retries: int = 3, initial_delay: float = 1.0, backoff_factor: float = 2.0):
    """
    Decorator that catches transient database errors, resets the connection,
    and retries the operation with exponential backoff.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if is_transient_db_error(e) and attempt < max_retries:
                        reset_connection()
                        time.sleep(delay)
                        delay *= backoff_factor
                        continue
                    # Retries exhausted or non-transient error
                    reset_connection()
                    st.error("A database connection error occurred. Please try again or contact admin@gkldevelopment.com.")
                    print(f"Database error in {func.__name__} (attempt {attempt}/{max_retries}): {e}")
                    return None
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
