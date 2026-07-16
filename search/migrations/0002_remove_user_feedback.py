from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("search", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="searchhistory",
            name="user_feedback",
        ),
    ]
