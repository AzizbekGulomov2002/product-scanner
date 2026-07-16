from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(model_name="product", name="brand"),
        migrations.RemoveField(model_name="product", name="description"),
        migrations.RemoveField(model_name="product", name="is_active"),
        migrations.RemoveField(model_name="product", name="category"),
        migrations.DeleteModel(name="Category"),
    ]
