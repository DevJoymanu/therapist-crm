from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0005_shareablelink"),
    ]

    operations = [
        migrations.AddField(
            model_name="patient",
            name="intake_submitted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="shareablelink",
            name="link_type",
            field=models.CharField(
                choices=[
                    ("consent", "Consent Form"),
                    ("booking", "Appointment Booking"),
                    ("intake", "Intake Form"),
                ],
                max_length=10,
            ),
        ),
    ]
