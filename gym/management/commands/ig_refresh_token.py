"""Refresh the Instagram access token (valid 60 days). Run it from a daily cron / Render Cron Job; the webhook also triggers it lazily."""
from django.core.management.base import BaseCommand, CommandError

from gym import instagram_api as ig


class Command(BaseCommand):
    help = "Instagram tokenini yangilaydi (60 kunlik). --force: muddat yetmagan bo'lsa ham."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true")

    def handle(self, *args, **opts):
        if not (ig.app_secret() and ig.verify_token() and ig.get_token()):
            raise CommandError("Instagram sozlanmagan (IG_APP_SECRET, IG_VERIFY_TOKEN, IG_ACCESS_TOKEN).")
        ok, msg = ig.refresh_token(force=opts["force"])
        (self.stdout if ok else self.stderr).write(f"Token: {msg}")
        if not ok:
            raise CommandError(msg)
