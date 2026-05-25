# Architecture Rules

## Module structure
The `crm` app is split into sub-packages. Every domain has its own folder.
Never put new logic back into a single large file.

```
crm/
├── models/
│   ├── __init__.py     ← re-exports all models
│   ├── base.py         ← TimeStampedModel
│   ├── patient.py      ← Patient, ClientConsent
│   ├── appointment.py  ← Appointment, AppointmentRequest
│   └── session.py      ← ScoringCriterion, SessionNote, ScoreEntry, ShareableLink
│
├── forms/
│   ├── __init__.py     ← re-exports all forms
│   ├── widgets.py      ← shared widgets and StyledModelForm base
│   ├── patients.py     ← PatientForm, ClientConsentForm, ClientIntakeForm, NewClientFullForm
│   ├── appointments.py ← AppointmentForm, ApproveRequestForm
│   ├── sessions.py     ← SessionNoteForm, ScoringCriterionForm
│   └── booking.py      ← NewClientBookingForm, ReturningClientBookingForm, PersonalizedBookingForm
│
├── services/
│   ├── __init__.py     ← re-exports all service functions
│   ├── querysets.py    ← patient_queryset_for, appointment_queryset_for, session_queryset_for
│   ├── scoring.py      ← scoring algorithm, risk classification, RISK_LEVELS
│   ├── dashboard.py    ← dashboard_context, patient_score_trends, latest_risk_for
│   └── notifications.py← notifications_for
│
├── views/
│   ├── __init__.py     ← re-exports all view classes (urls.py imports from here)
│   ├── base.py         ← TherapistRequiredMixin
│   ├── auth.py         ← RateLimitedLoginView
│   ├── dashboard.py    ← DashboardView
│   ├── patients.py     ← Patient CRUD views
│   ├── appointments.py ← Appointment CRUD, CalendarView, CalendarDayView
│   ├── sessions.py     ← Session CRUD, Criterion CRUD
│   └── booking.py      ← all public booking, consent, intake, shareable link views
│
├── admin.py            ← single file, fine as-is
├── urls.py             ← single file, fine as-is
├── middleware.py       ← single file, fine as-is
├── ratelimit.py        ← single file, fine as-is
└── context_processors.py
```

## Rules for new code

**Adding a new model:**
Put it in the most relevant existing module file. If it doesn't fit, create a new file
in `models/` and export it from `models/__init__.py`.

**Adding a new view:**
Add it to the most relevant existing file in `views/`. Export it from `views/__init__.py`.
Do not create a new view file unless the feature is a genuinely separate domain.

**Adding a new form:**
Same rule — add to the relevant `forms/` file.

**Adding new business logic:**
Goes in `services/`. Pure functions, no Django request/response objects.

## The __init__.py re-export pattern
Every package's `__init__.py` re-exports all public names so that external imports
(admin.py, urls.py, tests, migrations) never need to know which sub-file something
lives in. Always maintain this when adding new classes or functions.
