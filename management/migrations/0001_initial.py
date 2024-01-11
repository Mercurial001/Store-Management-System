# Generated by Django 3.2.23 on 2023-11-20 15:51

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('barcode', models.CharField(max_length=255)),
                ('price', models.IntegerField()),
                ('expiry_date', models.DateField()),
            ],
        ),
        migrations.CreateModel(
            name='SoldProducts',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('total_price', models.IntegerField()),
                ('date_sold', models.DateTimeField()),
                ('product', models.ManyToManyField(to='management.Product')),
            ],
        ),
        migrations.CreateModel(
            name='ScannedProducts',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('product', models.ManyToManyField(to='management.Product')),
            ],
        ),
    ]
