# Generated by Django 5.0.7 on 2024-07-24 21:32

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='App',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=300, null=True)),
                ('location', models.CharField(blank=True, max_length=300, null=True)),
                ('weight', models.IntegerField(blank=True, default=0, null=True)),
                ('color', models.CharField(blank=True, max_length=300, null=True)),
            ],
            options={
                'verbose_name_plural': 'Apps',
                'ordering': ('weight',),
            },
        ),
        migrations.CreateModel(
            name='Location',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=300, null=True)),
                ('zone', models.CharField(blank=True, max_length=300, null=True)),
                ('weight', models.IntegerField(blank=True, default=0, null=True)),
                ('color', models.CharField(blank=True, max_length=300, null=True)),
            ],
            options={
                'verbose_name_plural': 'Locations',
                'ordering': ('weight',),
            },
        ),
    ]
