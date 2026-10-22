from django.core.management.base import BaseCommand

from gym import telegram


class Command(BaseCommand):
    help = "Sends Telegram reminders (membership ending, class tomorrow, personal training). Schedule it hourly."

    def handle(self, *args, **opts):
        if not telegram.enabled():
            self.stdout.write("TELEGRAM_BOT_TOKEN is not set: nothing to send.")
            return
        sent = telegram.send_reminders()
        self.stdout.write(f"Sent: membership={sent['membership']}, class={sent['class']}, pt={sent['pt']}")
