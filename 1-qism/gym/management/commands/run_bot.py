import time

from django.core.management.base import BaseCommand, CommandError

from gym import telegram


class Command(BaseCommand):
    help = "Runs the Telegram bot (long polling). Keep it running next to the website."

    def handle(self, *args, **opts):
        if not telegram.enabled():
            raise CommandError("Set TELEGRAM_BOT_TOKEN first (get one from @BotFather).")
        self.stdout.write("Bot is running. Ctrl+C to stop.")
        offset = 0
        try:
            while True:
                new = telegram.run_bot_once(offset)
                if new == offset:
                    time.sleep(1)  # no updates (or an API error): avoid a tight loop
                offset = new
        except KeyboardInterrupt:
            pass
