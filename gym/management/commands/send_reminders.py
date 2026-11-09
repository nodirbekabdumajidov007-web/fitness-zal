from django.core.management.base import BaseCommand

from gym import extras, telegram


class Command(BaseCommand):
    help = ("Membership-ending reminders (7, 3 and 1 day before: site inbox, Telegram if linked, e-mail if enabled), class tomorrow and personal "
            "training. Idempotent: schedule it hourly or leave it to the dashboard, which runs it lazily once a day.")

    def handle(self, *args, **opts):
        sent = telegram.send_reminders()
        self.stdout.write(f"Sent (Telegram): membership={sent['membership']}, class={sent['class']}, pt={sent['pt']}")
        self.stdout.write(f"Telegram bot configured: {telegram.enabled()}")
