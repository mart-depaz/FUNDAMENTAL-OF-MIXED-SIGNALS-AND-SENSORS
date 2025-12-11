from django.db import migrations, models
import django.db.models.functions
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0032_add_qrcode_registration_model'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='qrcoderegistration',
            constraint=models.UniqueConstraint(
                fields=['qr_code'],
                name='uq_active_qr_code',
                condition=Q(is_active=True),
            ),
        ),
    ]
