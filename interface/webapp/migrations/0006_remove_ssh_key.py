from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [('webapp', '0005_chatline_featuredproject_image')]

    operations = [
        migrations.RemoveField(model_name='userprofile', name='ssh_public_key'),
    ]
