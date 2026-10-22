from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import RedirectView

urlpatterns = [
    path("django-admin/", admin.site.urls),
    # people naturally type /admin: send them to the real admin (which still asks for the ".admin" sign-in)
    re_path(r"^(?:admin|panel|adminka)/?$", RedirectView.as_view(url="/django-admin/", permanent=False)),
    path("", include("gym.urls")),
]
