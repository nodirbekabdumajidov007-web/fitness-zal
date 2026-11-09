"""Subscribe our Instagram account to the webhook fields (messages, seen, reactions, edits). Run once after the env vars are set."""
from django.core.management.base import BaseCommand, CommandError

from gym import instagram_api as ig


class Command(BaseCommand):
    help = "Instagram akkauntni webhook maydonlariga obuna qiladi (bir marta ishga tushiring)."

    def handle(self, *args, **opts):
        if not ig.configured():
            raise CommandError("Instagram sozlanmagan (IG_APP_SECRET, IG_VERIFY_TOKEN, IG_ACCESS_TOKEN).")
        try:
            res = ig.subscribe()
        except ig.ApiError as e:
            raise CommandError(f"Obuna bo'lmadi: {e}")
        self.stdout.write(f"Obuna: {res}  (maydonlar: {ig.SUBSCRIBED_FIELDS})")
