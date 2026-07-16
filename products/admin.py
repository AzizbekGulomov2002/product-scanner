from django.contrib import admin
from django.utils.html import format_html

from .models import ImportJob, Product, ProductImage


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    readonly_fields = ("has_embedding", "embedding_preview")
    fields = ("image", "is_primary", "has_embedding", "embedding_preview")

    def embedding_preview(self, obj):
        if obj.has_embedding:
            return format_html('<span style="color:green;">✓ Indexed</span>')
        return format_html('<span style="color:orange;">⏳ Pending</span>')

    embedding_preview.short_description = "Embedding"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "external_id",
        "name",
        "barcode",
        "image_count_display",
        "embedding_status_display",
        "created_at",
        "updated_at",
    )
    search_fields = ("external_id", "name", "barcode")
    inlines = [ProductImageInline]
    actions = ["reindex_embeddings"]

    def get_fields(self, request, obj=None):
        return ("external_id", "name", "barcode")

    def image_count_display(self, obj):
        return obj.image_count

    image_count_display.short_description = "Images"

    def embedding_status_display(self, obj):
        status = obj.embedding_status
        colors = {
            "complete": "green",
            "partial": "orange",
            "pending": "red",
            "no_images": "gray",
        }
        labels = {
            "complete": "Complete",
            "partial": "Partial",
            "pending": "Pending",
            "no_images": "No Images",
        }
        return format_html(
            '<span style="color:{};">{}</span>',
            colors.get(status, "gray"),
            labels.get(status, status),
        )

    embedding_status_display.short_description = "Embedding Status"

    @admin.action(description="Reindex embeddings for selected products")
    def reindex_embeddings(self, request, queryset):
        from search.tasks import enqueue_image_embedding
        from products.models import ProductImage

        count = 0
        for product in queryset:
            for image_id in ProductImage.objects.filter(product=product).values_list("id", flat=True):
                enqueue_image_embedding(image_id)
                count += 1
        self.message_user(
            request,
            f"Reindex queued for {count} image(s). Embedding status updates automatically.",
        )


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("product", "is_primary", "has_embedding", "created_at")
    list_filter = ("has_embedding", "is_primary")
    search_fields = ("product__name", "product__external_id")
    readonly_fields = ("has_embedding", "created_at")
    actions = ["generate_embeddings"]

    @admin.action(description="Generate embeddings for selected images")
    def generate_embeddings(self, request, queryset):
        from search.tasks import enqueue_image_embedding

        for image in queryset:
            enqueue_image_embedding(image.id)
        self.message_user(
            request,
            f"Embedding queued for {queryset.count()} image(s). Status updates when done.",
        )


@admin.register(ImportJob)
class ImportJobAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "status",
        "mode",
        "total_rows",
        "created_count",
        "updated_count",
        "error_count",
        "images_loaded",
        "progress_percent",
        "created_at",
    )
    list_filter = ("status", "mode")
    fields = ("excel_file", "zip_file", "mode")
    readonly_fields = (
        "status",
        "total_rows",
        "created_count",
        "updated_count",
        "error_count",
        "images_loaded",
        "progress_percent",
        "error_log",
        "started_at",
        "completed_at",
        "created_at",
    )
    change_form_template = "admin/products/importjob/change_form.html"

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return ()
        return self.readonly_fields

    def get_fields(self, request, obj=None):
        if obj is None:
            return ("excel_file", "zip_file", "mode")
        return (
            "excel_file",
            "zip_file",
            "mode",
            "status",
            "total_rows",
            "created_count",
            "updated_count",
            "error_count",
            "images_loaded",
            "progress_percent",
            "error_log",
            "started_at",
            "completed_at",
            "created_at",
        )

    def save_model(self, request, obj, form, change):
        is_new = obj.pk is None
        super().save_model(request, obj, form, change)
        if is_new and obj.status == "pending":
            from products.tasks import process_import_job
            import threading

            job_id = obj.id

            def _queue():
                try:
                    process_import_job.apply_async(args=[job_id], ignore_result=True)
                except Exception:
                    process_import_job.run(job_id)

            threading.Thread(target=_queue, daemon=True).start()
            self.message_user(request, f"Import #{job_id} queued in background.")
