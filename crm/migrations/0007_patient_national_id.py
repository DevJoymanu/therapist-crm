from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0006_patient_intake_submitted_at_shareablelink_intake"),
    ]

    operations = [
        migrations.AddField(
            model_name="patient",
            name="national_id",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Government-issued ID or passport number. Used to prevent duplicate records.",
                max_length=50,
                verbose_name="National ID / Passport No.",
            ),
            preserve_default=False,
        ),
    ]
