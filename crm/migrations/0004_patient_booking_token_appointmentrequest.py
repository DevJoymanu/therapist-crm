import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def populate_booking_tokens(apps, schema_editor):
    Patient = apps.get_model("crm", "Patient")
    for patient in Patient.objects.all():
        patient.booking_token = uuid.uuid4()
        patient.save(update_fields=["booking_token"])


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0003_patient_intake_fields_clientconsent"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Add without unique first (SQLite can't generate unique UUIDs per row via default)
        migrations.AddField(
            model_name="patient",
            name="booking_token",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=False),
        ),
        # Populate a unique UUID for each existing row
        migrations.RunPython(populate_booking_tokens, migrations.RunPython.noop),
        # Now enforce uniqueness
        migrations.AlterField(
            model_name="patient",
            name="booking_token",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.CreateModel(
            name="AppointmentRequest",
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
                ("client_first_name", models.CharField(max_length=80)),
                ("client_last_name", models.CharField(max_length=80)),
                ("client_phone", models.CharField(blank=True, max_length=40)),
                ("client_email", models.EmailField(blank=True, max_length=254)),
                ("preferred_date", models.DateField()),
                (
                    "preferred_time_slot",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("", "No preference"),
                            ("morning", "Morning (8am–12pm)"),
                            ("afternoon", "Afternoon (12pm–5pm)"),
                            ("evening", "Evening (after 5pm)"),
                        ],
                        max_length=10,
                    ),
                ),
                ("reason", models.TextField(blank=True)),
                ("is_new_client", models.BooleanField(default=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("approved", "Approved"),
                            ("declined", "Declined"),
                        ],
                        default="pending",
                        max_length=10,
                    ),
                ),
                ("therapist_response", models.TextField(blank=True)),
                ("token", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                (
                    "linked_appointment",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="booking_request",
                        to="crm.appointment",
                    ),
                ),
                (
                    "patient",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="appointment_requests",
                        to="crm.patient",
                    ),
                ),
                (
                    "therapist",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="appointment_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
