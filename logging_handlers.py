import logging
import time


class TelegramAlertHandler(logging.Handler):
    """Sends server errors to the admin Telegram chat, at most one message a minute. Silent when Telegram is not configured."""
    _last = 0.0

    def emit(self, record):
        try:
            from . import telegram
            if not telegram.enabled() or time.time() - TelegramAlertHandler._last < 60:
                return
            TelegramAlertHandler._last = time.time()
            telegram.alert_admin(f"Server xatosi ({record.levelname}): {record.getMessage()[:300]}")
        except Exception:
            self.handleError(record)
