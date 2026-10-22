from django.contrib.admin import apps


class GymAdminConfig(apps.AdminConfig):
    """Swaps Django's default admin site for ours, which adds the dashboard on the admin home page."""
    default_site = "gym.admin_site.GymAdminSite"

    def ready(self):
        super().ready()  # runs autodiscover: every app's admin.py is loaded by now
        from django.contrib import admin
        from django.contrib.auth.models import Group
        if admin.site.is_registered(Group):  # user groups are not used here (staff rights come from the "Xodim" tick)
            admin.site.unregister(Group)
