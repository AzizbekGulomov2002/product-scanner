from django.db import models
from pgvector.django import VectorField


class ImageEmbedding(models.Model):
    product_image = models.OneToOneField(
        "products.ProductImage",
        on_delete=models.CASCADE,
        related_name="embedding_record",
    )
    embedding = VectorField(dimensions=512)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Image Embedding"
        verbose_name_plural = "Image Embeddings"

    def __str__(self):
        return f"Embedding for {self.product_image}"


class SearchHistory(models.Model):
    RESULT_CHOICES = [
        ("found", "Product Found"),
        ("probable", "Probable Match"),
        ("not_found", "Not Found"),
        ("barcode", "Barcode Match"),
    ]
    SOURCE_CHOICES = [
        ("telegram", "Telegram Bot"),
        ("admin", "Admin Panel"),
        ("api", "API"),
        ("scanner", "Realtime Scanner"),
    ]

    query_image = models.ImageField(upload_to="queries/%Y/%m/", blank=True, null=True)
    detected_barcode = models.CharField(max_length=50, blank=True)
    matched_product = models.ForeignKey(
        "products.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="search_matches",
    )
    confidence = models.FloatField(null=True, blank=True)
    result_status = models.CharField(max_length=20, choices=RESULT_CHOICES, default="not_found")
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="api")
    telegram_user_id = models.CharField(max_length=50, blank=True)
    telegram_username = models.CharField(max_length=100, blank=True)
    raw_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Search History"
        verbose_name_plural = "Search History"
        ordering = ["-created_at"]

    def __str__(self):
        product_name = self.matched_product.name if self.matched_product else "None"
        return f"Search #{self.pk} -> {product_name} ({self.confidence})"
