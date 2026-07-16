import django.db.models.deletion
import pgvector.django
from django.db import migrations, models
from pgvector.django import VectorExtension


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("products", "0001_initial"),
    ]

    operations = [
        VectorExtension(),
        migrations.CreateModel(
            name="ImageEmbedding",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "embedding",
                    pgvector.django.VectorField(dimensions=512),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "product_image",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="embedding_record",
                        to="products.productimage",
                    ),
                ),
            ],
            options={
                "verbose_name": "Image Embedding",
                "verbose_name_plural": "Image Embeddings",
            },
        ),
        migrations.CreateModel(
            name="SearchHistory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("query_image", models.ImageField(blank=True, null=True, upload_to="queries/%Y/%m/")),
                ("detected_barcode", models.CharField(blank=True, max_length=50)),
                ("confidence", models.FloatField(blank=True, null=True)),
                (
                    "result_status",
                    models.CharField(
                        choices=[
                            ("found", "Product Found"),
                            ("probable", "Probable Match"),
                            ("not_found", "Not Found"),
                            ("barcode", "Barcode Match"),
                        ],
                        default="not_found",
                        max_length=20,
                    ),
                ),
                (
                    "source",
                    models.CharField(
                        choices=[
                            ("telegram", "Telegram Bot"),
                            ("admin", "Admin Panel"),
                            ("api", "API"),
                            ("scanner", "Realtime Scanner"),
                        ],
                        default="api",
                        max_length=20,
                    ),
                ),
                ("telegram_user_id", models.CharField(blank=True, max_length=50)),
                ("telegram_username", models.CharField(blank=True, max_length=100)),
                (
                    "user_feedback",
                    models.CharField(
                        choices=[
                            ("correct", "Correct"),
                            ("incorrect", "Incorrect"),
                            ("none", "No Feedback"),
                        ],
                        default="none",
                        max_length=20,
                    ),
                ),
                ("raw_response", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "matched_product",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="search_matches",
                        to="products.product",
                    ),
                ),
            ],
            options={
                "verbose_name": "Search History",
                "verbose_name_plural": "Search History",
                "ordering": ["-created_at"],
            },
        ),
    ]
