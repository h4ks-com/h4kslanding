from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("webapp", "0003_add_timezone_to_userprofile"),
    ]

    operations = [
        migrations.CreateModel(
            name="Announcement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("body", models.TextField()),
                ("author", models.CharField(max_length=100)),
                ("source", models.CharField(choices=[("admin", "Admin"), ("bot", "Bot")], default="admin", max_length=20)),
                ("pinned", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name_plural": "Announcements",
                "ordering": ["-pinned", "-created_at"],
            },
        ),
        migrations.CreateModel(
            name="FeaturedProject",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("url", models.CharField(max_length=500)),
                ("description", models.TextField()),
                ("tech_tags", models.CharField(blank=True, help_text="Comma-separated tags, e.g. python, IRC, asyncio", max_length=200)),
                ("color", models.CharField(blank=True, max_length=20)),
                ("weight", models.IntegerField(default=0)),
                ("active", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name_plural": "Featured Projects",
                "ordering": ["weight"],
            },
        ),
        migrations.CreateModel(
            name="ApiToken",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("token_hash", models.CharField(db_index=True, help_text="SHA-256 hash of the raw token", max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("active", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name_plural": "API Tokens",
            },
        ),
    ]
