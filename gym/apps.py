from django.apps import AppConfig


class GymConfig(AppConfig):
    name = "gym"
    verbose_name = "Fitnes Zal"

    def ready(self):
        from . import extras  # noqa: F401  (connects the waitlist signal)
