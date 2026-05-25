from .models import Appointment


def appointment_queryset_for(therapist):
    return Appointment.objects.filter(patient__therapist=therapist).select_related("patient")
