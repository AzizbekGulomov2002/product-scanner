from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

from search.views import (
    AddProductView,
    DashboardView,
    RealtimeScannerView,
    SearchView,
)

import config.admin_urls  # noqa: F401

urlpatterns = [
    path("", DashboardView.as_view(), name="home"),
    path("search/", SearchView.as_view(), name="search"),
    path("add/", AddProductView.as_view(), name="add-product"),
    path("scanner/", RealtimeScannerView.as_view(), name="scanner"),
    path("admin/", admin.site.urls),
    path("api/", include("search.urls")),
    path("api/", include("products.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
