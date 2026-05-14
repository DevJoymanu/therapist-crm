import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0002_scoringcriterion_weight"),
    ]

    operations = [
        migrations.RenameField(
            model_name="patient",
            old_name="emergency_contact",
            new_name="emergency_contact_name",
        ),
        migrations.RenameField(
            model_name="patient",
            old_name="medical_history",
            new_name="previous_treatment",
        ),
        migrations.AddField(
            model_name="patient",
            name="address",
            field=models.TextField(blank=True, default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="patient",
            name="current_medication",
            field=models.TextField(blank=True, default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="patient",
            name="emergency_contact_phone1",
            field=models.CharField(blank=True, default="", max_length=40),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="patient",
            name="emergency_contact_phone2",
            field=models.CharField(blank=True, default="", max_length=40),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="patient",
            name="emergency_contact_relationship",
            field=models.CharField(blank=True, default="", max_length=80),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="patient",
            name="gender",
            field=models.CharField(
                blank=True,
                choices=[("M", "Male"), ("F", "Female")],
                default="",
                max_length=1,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="patient",
            name="marital_status",
            field=models.CharField(
                blank=True,
                choices=[
                    ("single", "Single"),
                    ("married", "Married"),
                    ("divorced", "Divorced"),
                    ("widowed", "Widowed"),
                    ("separated", "Separated"),
                    ("other", "Other"),
                ],
                default="",
                max_length=10,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="patient",
            name="nationality",
            field=models.CharField(blank=True, default="", max_length=80),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="patient",
            name="occupation",
            field=models.CharField(blank=True, default="", max_length=80),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="patient",
            name="ok_to_contact_by_email",
            field=models.CharField(
                blank=True,
                choices=[("yes", "Yes"), ("no", "No")],
                default="",
                max_length=3,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="patient",
            name="ok_to_leave_message",
            field=models.CharField(
                blank=True,
                choices=[("yes", "Yes"), ("no", "No")],
                default="",
                max_length=3,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="patient",
            name="preferred_contact_method",
            field=models.CharField(
                blank=True,
                choices=[("email", "Email"), ("phone", "Phone")],
                default="",
                max_length=5,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="patient",
            name="referral_source",
            field=models.CharField(
                blank=True,
                choices=[
                    ("self", "No one (Self Referral)"),
                    ("friend", "Friend"),
                    ("family", "Family Member"),
                    ("partner", "Partner"),
                ],
                default="",
                max_length=7,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="patient",
            name="religion",
            field=models.CharField(blank=True, default="", max_length=80),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="patient",
            name="used_counselling_before",
            field=models.CharField(
                blank=True,
                choices=[("yes", "Yes"), ("no", "No")],
                default="",
                max_length=3,
            ),
            preserve_default=False,
        ),
        migrations.CreateModel(
            name="ClientConsent",
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
                ("client_name", models.CharField(blank=True, max_length=160)),
                ("client_signed_date", models.DateField(blank=True, null=True)),
                ("counsellor_signed_date", models.DateField(blank=True, null=True)),
                (
                    "patient",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="consent",
                        to="crm.patient",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
    ]
