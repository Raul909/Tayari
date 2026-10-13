from slowapi import Limiter

from app.net import client_ip

# Per-client rate limits. Keyed on the real client address (see app/net.py), not
# the socket peer — behind Render's proxy that peer is the same for everyone.
limiter = Limiter(
    key_func=client_ip,
    default_limits=["60/minute", "1000/hour"],
    storage_uri="memory://",
)
