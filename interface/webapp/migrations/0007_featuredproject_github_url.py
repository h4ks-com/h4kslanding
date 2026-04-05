from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('webapp', '0006_remove_ssh_key')]

    operations = [
        migrations.AddField(
            model_name='featuredproject',
            name='github_url',
            field=models.CharField(blank=True, max_length=500, help_text='GitHub repository URL, e.g. https://github.com/h4ks-com/CloudBot'),
        ),
    ]
