from django.contrib import admin
from django.template.response import TemplateResponse
from django.urls import path

from search.admin import get_dashboard_stats


def dashboard_view(request):
    stats = get_dashboard_stats()
    return TemplateResponse(
        request,
        "admin/dashboard.html",
        {**admin.site.each_context(request), "stats": stats, "title": "Dashboard"},
    )


def search_test_view(request):
    return TemplateResponse(
        request,
        "admin/search_test.html",
        {**admin.site.each_context(request), "title": "Search Test"},
    )


def bulk_import_view(request):
    from products.models import ImportJob

    recent_jobs = ImportJob.objects.all()[:10]
    return TemplateResponse(
        request,
        "admin/bulk_import.html",
        {
            **admin.site.each_context(request),
            "title": "Bulk Import",
            "recent_jobs": recent_jobs,
        },
    )


original_get_urls = admin.site.get_urls


def custom_get_urls():
    custom_urls = [
        path("dashboard/", admin.site.admin_view(dashboard_view), name="dashboard"),
        path("search-test/", admin.site.admin_view(search_test_view), name="search-test"),
        path("bulk-import/", admin.site.admin_view(bulk_import_view), name="bulk-import"),
    ]
    return custom_urls + original_get_urls()


admin.site.get_urls = custom_get_urls

from search import admin as search_admin  # noqa: E402, F401
from products import admin as products_admin  # noqa: E402, F401
