import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0004_patient_booking_token_appointmentrequest"),
    ]

    operations = [
        migrations.CreateModel(
            name="ShareableLink",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("token", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                (
                    "link_type",
                    models.CharField(
                        choices=[("consent", "Consent Form"), ("booking", "Appointment Booking")],
                        max_length=10,
                    ),
                ),
                ("expires_at", models.DateTimeField()),
                (
                    "patient",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="shareable_links",
                        to="crm.patient",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
