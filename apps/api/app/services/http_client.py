from functools import lru_cache

import httpx


@lru_cache(maxsize=1)
def outbound_http_client() -> httpx.Client:
    """Reuse DNS, TLS, and keep-alive connections for external AI requests."""
    return httpx.Client(
        follow_redirects=True,
        limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
        timeout=httpx.Timeout(30.0, connect=10.0),
    )
