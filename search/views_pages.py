from django.views.generic import TemplateView


class DashboardView(TemplateView):
    template_name = "app/dashboard.html"


class SearchView(TemplateView):
    template_name = "app/search.html"


class AddProductView(TemplateView):
    template_name = "app/add.html"


class RealtimeScannerView(TemplateView):
    template_name = "scanner/realtime.html"
