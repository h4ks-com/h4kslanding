from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("webapp", "0004_announcement_featuredproject_apitoken"),
    ]

    operations = [
        migrations.CreateModel(
            name="ChatLine",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nick", models.CharField(max_length=100)),
                ("message", models.TextField()),
                ("channel", models.CharField(default="#lobby", max_length=100)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name_plural": "Chat Lines",
                "ordering": ["created_at"],
            },
        ),
        migrations.AddField(
            model_name="featuredproject",
            name="image",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="projects/",
                help_text="Project screenshot or logo",
            ),
        ),
    ]
