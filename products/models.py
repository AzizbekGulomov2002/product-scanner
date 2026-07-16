from django.db import models


class Product(models.Model):
    external_id = models.CharField(max_length=100, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    barcode = models.CharField(max_length=50, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.name} ({self.external_id})"

    @property
    def image_count(self):
        return self.images.count()

    @property
    def embedding_status(self):
        total = self.images.count()
        if total == 0:
            return "no_images"
        with_emb = self.images.filter(has_embedding=True).count()
        if with_emb == 0:
            return "pending"
        if with_emb < total:
            return "partial"
        return "complete"


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(upload_to="products/%Y/%m/")
    is_primary = models.BooleanField(default=False)
    has_embedding = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Product Image"
        verbose_name_plural = "Product Images"
        ordering = ["-is_primary", "created_at"]

    def __str__(self):
        return f"Image for {self.product.name}"


class ImportJob(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]
    MODE_CHOICES = [
        ("create", "Create Only"),
        ("update", "Update Only"),
        ("create_update", "Create or Update"),
    ]

    excel_file = models.FileField(upload_to="imports/excel/")
    zip_file = models.FileField(upload_to="imports/zip/", blank=True, null=True)
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default="create_update")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    total_rows = models.IntegerField(default=0)
    created_count = models.IntegerField(default=0)
    updated_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    images_loaded = models.IntegerField(default=0)
    progress_percent = models.IntegerField(default=0)
    error_log = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Import"
        verbose_name_plural = "Import"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Import #{self.pk} - {self.status}"
