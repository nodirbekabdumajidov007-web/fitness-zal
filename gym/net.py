"""The address of the person behind a request.

On Render every request reaches the app through the platform's proxy, so REMOTE_ADDR is the proxy and all visitors would share one rate-limit
bucket (one guest's attempts would block everybody, and brute-force protection would count per proxy, not per attacker). The proxy puts the
visitor's address in X-Forwarded-For, so behind a proxy we read it from there.

The header is trusted only when we know a proxy of ours sets it: on Render (the RENDER environment variable) or when TRUST_PROXY_HEADERS is
switched on in the settings (env FZ_TRUST_PROXY=1) for another host behind a proxy. On a plain server (start.bat, tests) a client could
send the header itself, so REMOTE_ADDR is used.
"""
import ipaddress
import os

from django.conf import settings


def behind_proxy():
    """True when X-Forwarded-For comes from our own proxy (checked on every call, so tests can switch it)."""
    return bool(getattr(settings, "TRUST_PROXY_HEADERS", False) or os.environ.get("RENDER"))


def _valid_ip(text):
    """The canonical form of `text` when it is an IPv4 / IPv6 address, else None (garbage, hostnames, "unknown" are skipped)."""
    text = text.strip()
    if not text or len(text) > 45:
        return None
    try:
        return str(ipaddress.ip_address(text))
    except ValueError:
        return None


def client_ip(request):
    """The visitor's IP as a string: the left-most valid address of X-Forwarded-For when behind our proxy, else REMOTE_ADDR ("" when unknown).

    Trade-off: the left-most entry is the one the visitor's own request started with, so a visitor can write a made-up address there and
    the proxy keeps it in front. That is the usual convention and gives every real visitor a separate bucket, but an attacker who rotates
    the header can dodge a per-IP limit; the login limits therefore also count per account, not only per address."""
    remote = request.META.get("REMOTE_ADDR", "") or ""
    if behind_proxy():
        for part in (request.META.get("HTTP_X_FORWARDED_FOR", "") or "")[:1000].split(","):
            ip = _valid_ip(part)
            if ip:
                return ip
    return _valid_ip(remote) or remote
