"""Lightweight observability helpers: .env loading, optional Sentry, and
Healthchecks.io pings. Everything degrades to a clean no-op when a piece is
absent (no DSN, sentry_sdk not installed, no ping URL), so monitoring can never
break the app or the scrape.

Secrets are read from the environment only — populate a gitignored
`.env` next to this file (KEY=VALUE lines) on the server; never commit them.
"""
import os


def load_dotenv(path=None):
    """Load KEY=VALUE lines from a local .env into os.environ without overriding
    variables already set in the real environment. Silent if the file is missing.
    Lets cron and PM2 pick up secrets from one file."""
    path = path or os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key:
                    os.environ.setdefault(key, val)
    except FileNotFoundError:
        pass
    except Exception:
        # A malformed .env must never crash startup.
        pass


def init_sentry(environment="production"):
    """Initialize Sentry if SENTRY_DSN is set and sentry_sdk is installed.
    Returns True if enabled, False otherwise. Never raises."""
    dsn = os.environ.get("SENTRY_DSN")
    if not dsn:
        return False
    try:
        import sentry_sdk
        sentry_sdk.init(dsn=dsn, traces_sample_rate=0.1, environment=environment)
        return True
    except Exception:
        return False


def capture_exception(exc):
    """Report an exception to Sentry if available; no-op otherwise."""
    try:
        import sentry_sdk
        sentry_sdk.capture_exception(exc)
    except Exception:
        pass


def capture_message(message, level="error"):
    """Report a message to Sentry if available; no-op otherwise."""
    try:
        import sentry_sdk
        sentry_sdk.capture_message(message, level=level)
    except Exception:
        pass


def ping_healthchecks(success=True):
    """Ping the Healthchecks.io URL in HC_SCRAPE_PING_URL. On failure, append
    /fail so a silent-but-wrong scrape still raises an alert. Never raises and
    never blocks (short timeout)."""
    url = os.environ.get("HC_SCRAPE_PING_URL")
    if not url:
        return
    try:
        import requests
        target = url if success else url.rstrip("/") + "/fail"
        requests.get(target, timeout=10)
    except Exception:
        pass
