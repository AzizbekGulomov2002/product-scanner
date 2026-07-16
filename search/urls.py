from django.urls import path

from search.views import (
    AdminSearchTestView,
    BarcodeSearchView,
    DashboardStatsView,
    ImageSearchView,
    RealtimeFrameSearchView,
)

urlpatterns = [
    path("search/image/", ImageSearchView.as_view(), name="search-image"),
    path("search/barcode/", BarcodeSearchView.as_view(), name="search-barcode"),
    path("search/realtime/", RealtimeFrameSearchView.as_view(), name="search-realtime"),
    path("search/test/", AdminSearchTestView.as_view(), name="search-test"),
    path("dashboard/stats/", DashboardStatsView.as_view(), name="dashboard-stats"),
]
