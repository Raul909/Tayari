"""
Who is actually calling.

On Render the socket peer is never the user. A request crosses Cloudflare (Render's
own edge, and now Tayari's edge gateway as well) and then Render's load balancer,
so `request.client.host` is an internal address shared by every visitor. Keying
the rate limiter on it put the whole world in one bucket: sixty profile requests
a minute, total, and the sixty-first person in a flood zone got a 429.

The fix is the standard trusted-proxy walk. Each proxy appends the address it
received the connection from to X-Forwarded-For, so reading the list from the
right and skipping hops we know are proxies lands on the first address nobody we
trust vouched for — the client. Reading from the left instead would let anyone
choose their own rate-limit key by sending a forged header.
"""

import ipaddress
from functools import lru_cache

from starlette.requests import Request

# Cloudflare's published ranges (cloudflare.com/ips). They change rarely; a
# stale entry only means one proxy hop is mistaken for a client, which costs
# rate-limit precision, never correctness of a response.
_CLOUDFLARE = [
    "173.245.48.0/20", "103.21.244.0/22", "103.22.200.0/22", "103.31.4.0/22",
    "141.101.64.0/18", "108.162.192.0/18", "190.93.240.0/20", "188.114.96.0/20",
    "197.234.240.0/22", "198.41.128.0/17", "162.158.0.0/15", "104.16.0.0/13",
    "104.24.0.0/14", "172.64.0.0/13", "131.0.72.0/22",
    "2400:cb00::/32", "2606:4700::/32", "2803:f800::/32", "2405:b500::/32",
    "2405:8100::/32", "2a06:98c0::/29", "2c0f:f248::/32",
]
_TRUSTED_NETWORKS = [ipaddress.ip_network(n) for n in _CLOUDFLARE]


@lru_cache(maxsize=4096)
def _is_proxy(address: str) -> bool:
    """True for Cloudflare, private, loopback and link-local addresses."""
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        # Not an address at all (an "unknown" token, a port suffix we did not
        # strip): skip it rather than let garbage become someone's bucket.
        return True
    if ip.is_private or ip.is_loopback or ip.is_link_local:
        return True
    return any(ip in net for net in _TRUSTED_NETWORKS)


def client_ip(request: Request) -> str:
    """The best available address for the end user behind our proxies."""
    forwarded = request.headers.get("x-forwarded-for", "")
    hops = [h.strip() for h in forwarded.split(",") if h.strip()]
    for hop in reversed(hops):
        if not _is_proxy(hop):
            return hop
    # Every hop was a proxy (or there were none): fall back to what Cloudflare
    # says, then to the socket peer, so local development still works.
    return (
        request.headers.get("cf-connecting-ip")
        or (request.client.host if request.client else "unknown")
    )
