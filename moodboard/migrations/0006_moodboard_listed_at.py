# Generated by Django 3.2.18 on 2023-10-23 14:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('moodboard', '0005_auto_20231020_1421'),
    ]

    operations = [
        migrations.AddField(
            model_name='moodboard',
            name='listed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]