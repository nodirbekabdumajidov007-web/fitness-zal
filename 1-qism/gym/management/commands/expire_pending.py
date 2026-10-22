from django.core.management.base import BaseCommand

from gym import services


class Command(BaseCommand):
    help = "Cancels card transfers nobody reported within 24 hours and returns the reserved stock. Schedule it hourly."

    def handle(self, *args, **opts):
        self.stdout.write(f"Cancelled: {services.expire_pending()}")
