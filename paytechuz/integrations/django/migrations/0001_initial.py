# payments/migrations/0001_initial.py

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='PaymentTransaction',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('gateway', models.CharField(choices=[('payme', 'Payme'), ('click', 'Click')], max_length=10)),
                ('transaction_id', models.CharField(max_length=255)),
                ('account_id', models.CharField(max_length=255)),
                ('amount', models.DecimalField(max_digits=15, decimal_places=2)),
                ('state', models.IntegerField(choices=[
                    (0, 'Created'),
                    (1, 'Initiating'),
                    (2, 'Successfully'),
                    (-2, 'Cancelled after successful performed'),
                    (-1, 'Cancelled during initiation'),
                ], default=0)),
                ('reason', models.IntegerField(blank=True, null=True)),
                ('extra_data', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True)),
                ('performed_at', models.DateTimeField(blank=True, null=True, db_index=True)),
                ('cancelled_at', models.DateTimeField(blank=True, null=True, db_index=True)),
            ],
            options={
                'verbose_name': 'Payment Transaction',
                'verbose_name_plural': 'Payment Transactions',
                'ordering': ['-created_at'],
                'db_table': 'payments',
                'unique_together': {('gateway', 'transaction_id')},
            },
        ),
    ]
