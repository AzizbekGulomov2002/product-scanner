from django.urls import path

from .views import ProductCreateView, ProductDetailView, ProductLookupView

urlpatterns = [
    path("products/lookup/", ProductLookupView.as_view(), name="product-lookup"),
    path("products/create/", ProductCreateView.as_view(), name="product-create"),
    path("products/<int:pk>/", ProductDetailView.as_view(), name="product-detail"),
]
