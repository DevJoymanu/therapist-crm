# Testing Rules

## The core rule
Every feature added or changed ships with tests in the same task. Never as a follow-up.
Write tests even if the user forgets to ask for them.

## Why this matters
The user's primary concern is regressions — existing working features breaking silently
when new things are added. Tests are the safety net that catches this before the browser does.

## What to test

**Highest priority — data isolation (security)**
A therapist must never see another therapist's patients, appointments, sessions, or any
other data. Every view that queries data must be tested with a second therapist who should
get a 404, not their data.

**High priority — public endpoints**
The booking portal, consent form, intake form, and shareable links are client-facing and
require no login. They must keep working after every change.

**Medium priority — business logic with rules**
Scoring algorithm (already covered), form validation edge cases, shareable link expiry,
appointment conflict detection.

**Low priority — plain CRUD views**
Standard Django create/update/delete views break loudly and visibly. Less value testing
these exhaustively.

## Test structure for this project

```
crm/tests/
├── test_scoring.py        ← service logic (5 tests already exist here)
├── test_access_control.py ← auth enforcement + therapist data isolation for every URL
├── test_views_smoke.py    ← every protected page loads (200) with correct context
└── test_public_flows.py   ← booking portal, consent, shareable links end-to-end
```

## Current status
- `test_scoring.py` — 5 tests written, all passing
- `test_access_control.py` — NOT YET WRITTEN (highest priority gap)
- `test_views_smoke.py` — NOT YET WRITTEN
- `test_public_flows.py` — NOT YET WRITTEN

The regression baseline suite still needs to be written. Offer to write it before starting
any new feature work if it hasn't been done yet.

## Naming convention
- Test methods: `test_<what_it_does>` — e.g. `test_patient_detail_returns_404_for_wrong_therapist`
- Test classes: `<Feature>Tests` — e.g. `PatientAccessTests`, `BookingPortalTests`
