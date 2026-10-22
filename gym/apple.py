"""Sign in with Apple: checks the id_token Apple's JS hands the browser.

The token is a JWT signed with RS256 by one of Apple's public keys (https://appleid.apple.com/auth/keys). We verify the
signature ourselves with plain integer RSA (PKCS#1 v1.5 + SHA-256), so no crypto package is needed, and then check the
issuer, the audience (our Services ID) and the expiry. Nothing in the token is trusted before the signature checks out."""
import base64
import hashlib
import hmac
import json
import time
import urllib.request

from django.core.cache import cache

ISSUER = "https://appleid.apple.com"
KEYS_URL = "https://appleid.apple.com/auth/keys"
SHA256_PREFIX = bytes.fromhex("3031300d060960864801650304020105000420")  # DER DigestInfo header for SHA-256


def _b64(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _keys():
    keys = cache.get("apple:jwks")
    if keys is None:
        with urllib.request.urlopen(KEYS_URL, timeout=6) as r:
            keys = json.load(r)["keys"]
        cache.set("apple:jwks", keys, 6 * 3600)
    return keys


def _rsa_ok(n, e, signed, sig):
    k = (n.bit_length() + 7) // 8
    if len(sig) != k:
        return False
    em = pow(int.from_bytes(sig, "big"), e, n).to_bytes(k, "big")
    digest = SHA256_PREFIX + hashlib.sha256(signed).digest()
    expected = b"\x00\x01" + b"\xff" * (k - len(digest) - 3) + b"\x00" + digest
    return hmac.compare_digest(em, expected)


def verify(token, client_id, keys=None, now=None):
    """Returns the token's claims, or None if anything is off."""
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
    except Exception:
        return None
    now = now or time.time()
    if claims.get("iss") != ISSUER or claims.get("aud") != client_id or float(claims.get("exp", 0)) < now:
        return None
    if not claims.get("sub"):
        return None
    return claims
