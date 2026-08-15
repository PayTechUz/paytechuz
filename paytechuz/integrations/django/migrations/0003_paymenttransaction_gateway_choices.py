from django.db import migrations, models


class Migration(migrations.Migration):
    """Sync the gateway choices with the current PaymentTransaction model."""

    dependencies = [
        ('django', '0002_alter_paymenttransaction_gateway'),
    ]

    operations = [
        migrations.AlterField(
            model_name='paymenttransaction',
            name='gateway',
            field=models.CharField(
                choices=[
                    ('payme', 'Payme'),
                    ('click', 'Click'),
                    ('uzum', 'Uzum'),
                    ('paynet', 'Paynet'),
                    ('octo', 'Octo'),
                ],
                max_length=10,
            ),
        ),
    ]
