"""Send again the Instagram replies that failed earlier (still inside the 24 hour window)."""
from django.core.management.base import BaseCommand

from gym import instagram_api as ig
from gym import instagram_bot as bot


class Command(BaseCommand):
    help = "Yuborilmay qolgan Instagram javoblarini qayta yuboradi."

    def handle(self, *args, **opts):
        if not ig.configured():
            self.stdout.write("Instagram sozlanmagan.")
            return
        self.stdout.write(f"Qayta urinildi: {bot.retry_pending(limit=50)}")
