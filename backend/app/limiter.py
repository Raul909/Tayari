from slowapi import Limiter
from slowapi.util import get_remote_address

# Global rate limiter using client IP address
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["60/minute", "1000/hour"],
    storage_uri="memory://",
)
