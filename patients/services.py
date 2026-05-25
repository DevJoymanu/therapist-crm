from .models import Patient


def patient_queryset_for(therapist):
    return Patient.objects.filter(therapist=therapist)
