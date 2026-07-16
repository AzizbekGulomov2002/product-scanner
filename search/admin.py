from django.contrib import admin
from django.db.models import Avg
from django.utils import timezone
from django.utils.html import format_html

from search.models import ImageEmbedding, SearchHistory


@admin.register(SearchHistory)
class SearchHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "thumbnail",
        "matched_product",
        "confidence_display",
        "result_status",
        "source",
        "telegram_username",
        "created_at",
    )
    list_filter = ("result_status", "source")
    readonly_fields = (
        "query_image",
        "detected_barcode",
        "matched_product",
        "confidence",
        "result_status",
        "source",
        "telegram_user_id",
        "telegram_username",
        "raw_response",
        "created_at",
    )
    search_fields = ("matched_product__name", "telegram_username", "detected_barcode")

    def thumbnail(self, obj):
        if obj.query_image:
            return format_html(
                '<img src="{}" width="60" height="60" style="object-fit:cover;border-radius:4px;" />',
                obj.query_image.url,
            )
        return "-"

    thumbnail.short_description = "Query Image"

    def confidence_display(self, obj):
        if obj.confidence is None:
            return "-"
        pct = round(obj.confidence * 100, 1)
        color = "green" if pct >= 85 else "orange" if pct >= 70 else "red"
        return format_html('<span style="color:{};">{}%</span>', color, pct)

    confidence_display.short_description = "Confidence"


@admin.register(ImageEmbedding)
class ImageEmbeddingAdmin(admin.ModelAdmin):
    list_display = ("product_image", "created_at", "updated_at")
    readonly_fields = ("product_image", "embedding", "created_at", "updated_at")


def get_dashboard_stats():
    from products.models import Product, ProductImage

    today = timezone.now().date()
    total_products = Product.objects.count()
    total_images = ProductImage.objects.count()
    without_embedding = ProductImage.objects.filter(has_embedding=False).count()
    today_searches = SearchHistory.objects.filter(created_at__date=today).count()
    found_today = SearchHistory.objects.filter(
        created_at__date=today,
        result_status__in=["found", "barcode"],
    ).count()
    not_found_today = SearchHistory.objects.filter(
        created_at__date=today,
        result_status="not_found",
    ).count()
    avg_confidence = SearchHistory.objects.filter(
        confidence__isnull=False,
    ).aggregate(avg=Avg("confidence"))["avg"]

    return {
        "total_products": total_products,
        "total_images": total_images,
        "without_embedding": without_embedding,
        "today_searches": today_searches,
        "found_today": found_today,
        "not_found_today": not_found_today,
        "avg_confidence": round(avg_confidence * 100, 1) if avg_confidence else 0,
    }
