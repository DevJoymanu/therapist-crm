from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from crm.models import Appointment, Patient, ScoreEntry, SessionNote
from crm.services import criteria_for


class Command(BaseCommand):
    help = "Create demo therapist CRM data for local development."

    def handle(self, *args, **options):
        User = get_user_model()
        therapist, created = User.objects.get_or_create(
            username="therapist",
            defaults={"email": "therapist@example.com"},
        )
        if created:
            therapist.set_password("therapist123")
            therapist.save(update_fields=["password"])

        criteria = list(criteria_for(therapist))
        patients = [
            {
                "first_name": "Maya",
                "last_name": "Singh",
                "email": "maya@example.com",
                "phone": "+1 555 0101",
                "medical_history": "Generalized anxiety; no current medication changes.",
            },
            {
                "first_name": "Jonah",
                "last_name": "Reed",
                "email": "jonah@example.com",
                "phone": "+1 555 0102",
                "medical_history": "Depression history; safety plan reviewed.",
            },
            {
                "first_name": "Elena",
                "last_name": "Morales",
                "email": "elena@example.com",
                "phone": "+1 555 0103",
                "medical_history": "Work stress and sleep disruption.",
            },
        ]

        for index, data in enumerate(patients):
            patient, _ = Patient.objects.get_or_create(
                therapist=therapist,
                first_name=data["first_name"],
                last_name=data["last_name"],
                defaults=data,
            )
            starts_at = timezone.now() + timedelta(days=index, hours=2)
            Appointment.objects.get_or_create(
                patient=patient,
                starts_at=starts_at,
                defaults={
                    "ends_at": starts_at + timedelta(minutes=50),
                    "location": "Room 2",
                    "reminder_email": True,
                },
            )
            for week in range(3):
                session, _ = SessionNote.objects.get_or_create(
                    patient=patient,
                    session_date=timezone.localdate() - timedelta(days=(3 - week) * 7),
                    defaults={
                        "presenting_concerns": "Reviewed current stressors and coping skills.",
                        "interventions": "CBT reframing, grounding exercise, treatment goal review.",
                        "plan": "Continue weekly practice and review symptom tracking next session.",
                    },
                )
                for criterion in criteria:
                    base = 4 + week + index
                    value = min(criterion.max_score, base)
                    if criterion.name.lower().startswith("risk"):
                        value = 8 if patient.last_name == "Reed" and week == 2 else max(1, 5 - week)
                    ScoreEntry.objects.get_or_create(
                        session=session,
                        criterion=criterion,
                        defaults={"value": value},
                    )

        self.stdout.write(self.style.SUCCESS("Demo data ready. Login: therapist / therapist123"))
