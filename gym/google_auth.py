"""Google sign-in: checks the ID token (a JWT) that Google Identity Services hands the browser.

Why not the `tokeninfo` endpoint: it is meant for debugging, adds a network call to Google's servers on every sign-in and Google may
throttle it. Instead the RS256 signature is verified locally against Google's public keys (JWKS, cached 6 hours), reusing the plain-integer
RSA check already used for Apple (gym/apple.py), so no new dependency is needed. Then the issuer, the audience (our Client ID), the expiry
and the verified e-mail are checked. Nothing in the token is trusted before the signature checks out."""
import json
import time
import urllib.request

from django.core.cache import cache

from .apple import _b64, _rsa_ok

ISSUERS = ("accounts.google.com", "https://accounts.google.com")
KEYS_URL = "https://www.googleapis.com/oauth2/v3/certs"


def _keys():
    keys = cache.get("google:jwks")
    if keys is None:
        with urllib.request.urlopen(KEYS_URL, timeout=6) as r:
            keys = json.load(r)["keys"]
        cache.set("google:jwks", keys, 6 * 3600)
    return keys


def verify(token, client_id, keys=None, now=None):
    """The token's claims when it is genuine, was issued for `client_id`, is not expired and carries a verified e-mail; else None."""
    try:
        head_b64, body_b64, sig_b64 = token.split(".")
        head = json.loads(_b64(head_b64))
        if head.get("alg") != "RS256":
            return None
        key = next((k for k in (keys if keys is not None else _keys()) if k.get("kid") == head.get("kid") and k.get("kty") == "RSA"), None)
        if not key:
            return None
        n, e = int.from_bytes(_b64(key["n"]), "big"), int.from_bytes(_b64(key["e"]), "big")
        if not _rsa_ok(n, e, f"{head_b64}.{body_b64}".encode(), _b64(sig_b64)):
            return None
        claims = json.loads(_b64(body_b64))
        if claims.get("iss") not in ISSUERS or claims.get("aud") != client_id or float(claims.get("exp", 0)) < (now or time.time()):
            return None
        if not claims.get("email") or str(claims.get("email_verified")).lower() != "true":
            return None
    except Exception:
        return None
    return claims
