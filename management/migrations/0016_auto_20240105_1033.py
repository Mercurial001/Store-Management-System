# Generated by Django 3.2.23 on 2024-01-05 02:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('management', '0015_notification_identifier'),
    ]

    operations = [
        migrations.AddField(
            model_name='soldproducts',
            name='cash',
            field=models.IntegerField(null=True),
        ),
        migrations.AddField(
            model_name='soldproducts',
            name='change',
            field=models.IntegerField(null=True),
        ),
    ]
