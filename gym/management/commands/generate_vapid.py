"""Prints a new VAPID key pair for Web Push. Paste the two lines into the host's environment (Render -> Environment); never commit them."""
import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from django.core.management.base import BaseCommand


def b64url(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def new_pair():
    key = ec.generate_private_key(ec.SECP256R1())
    private = b64url(key.private_numbers().private_value.to_bytes(32, "big"))
    public = b64url(key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint))
    return public, private


class Command(BaseCommand):
    help = "Generate a VAPID key pair (VAPID_PUBLIC_KEY / VAPID_PRIVATE_KEY) for Web Push notifications"

    def handle(self, *args, **opts):
        public, private = new_pair()
        self.stdout.write("Add these to the environment of the server (Render -> Environment). Keep the private key secret; do not commit it.\n")
        self.stdout.write(f"VAPID_PUBLIC_KEY={public}")
        self.stdout.write(f"VAPID_PRIVATE_KEY={private}")
        self.stdout.write("VAPID_SUBJECT=mailto:you@example.com   (optional: a contact address for push services)")
        self.stdout.write("\nChanging the keys later invalidates every existing subscription: members must switch notifications on again.")
