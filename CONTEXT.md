# CONTEXT.md — Academic Timetable Portal

**Last Updated:** June 2026  
**Stack:** Flask · MySQL · Vanilla HTML/CSS/JS · Genetic Algorithm

---

## Project Overview

The Academic Timetable Portal is a multi-tenant, AI-powered timetable management system for academic institutions. Each registered institution (school) manages its own:

- Faculty (teachers)
- Classes and semesters
- Subjects with credit hours
- Schedule configuration (start/end times, break periods)
- Holiday/blocked days
- Timetables generated via a Genetic Algorithm engine

The system is designed so that **faculty conflict prevention is a hard constraint** — a faculty member can never be assigned to two classes at the same (day, time).

---

## Architecture

```
app.py                          ← Flask entry point, blueprint registration
├── src/
│   ├── auth/auth.py            ← Login, register, logout, delete account
│   ├── routes/
│   │   ├── main.py             ← Home, dashboard
│   │   ├── management.py       ← Manage teachers, subjects, timings, holidays
│   │   ├── generation.py       ← Generate and regenerate timetables
│   │   ├── timetable.py        ← View, modify, get timetable APIs
│   │   └── faculty.py          ← Faculty timetable + workload analytics
│   ├── services/
│   │   └── timetable_service.py ← Core generation orchestration + validation
│   ├── logic/
│   │   ├── algorithms.py       ← Genetic Algorithm implementation
│   │   └── config.py           ← DB + app config from .env
│   ├── database/
│   │   └── database.py         ← DB connection + shared queries
│   └── utils/
│       └── decorators.py       ← @login_required decorator
└── frontend/
    ├── templates/              ← Jinja2 HTML templates
    └── static/                 ← style.css, images
```

---

## Database Schema

| Table              | Purpose                                              |
|--------------------|------------------------------------------------------|
| `schools`          | Multi-tenant root. Stores schedule config per school |
| `teacher`          | Faculty members linked to school_id                  |
| `class`            | Batch/class groups linked to school_id               |
| `course`           | Course grouping (used as org unit, 1 per school)     |
| `subject`          | Subjects with credits, teacher_id, class_id, semester|
| `timeslot`         | Canonical list of time slots (HH:MM:SS, type)        |
| `timetable`        | Generated schedule: teacher × subject × class × day × time |
| `school_holidays`  | Blocked days per school (e.g. Sunday-equivalent)     |
| `allocated_timeslots` | Legacy (allocated slot tracking — not currently used in GA) |
| `practical`        | Practical sessions (future use)                      |
| `room`             | Room management (future use)                         |

**Key relationships:**
- `subject.teacher_id → teacher.teacher_id` — who teaches each subject
- `timetable.teacher_id` — denormalised teacher reference for fast conflict queries
- `timetable.class_id` — which class does this slot belong to

---

## Route Structure

| Method | URL                          | Blueprint    | Purpose                              |
|--------|------------------------------|--------------|--------------------------------------|
| GET    | `/`                          | main         | Landing page                         |
| GET    | `/dashboard`                 | main         | Institution dashboard                |
| GET    | `/manage_teachers`           | management   | Faculty CRUD                         |
| GET    | `/manage_subjects`           | management   | Subject + class CRUD                 |
| GET    | `/manage_timings`            | management   | Schedule config + holidays           |
| GET    | `/generate_setup`            | generation   | Timetable generation UI              |
| POST   | `/generate`                  | generation   | Run GA, return JSON with report      |
| GET    | `/regenerate_quick`          | generation   | Regenerate with same context         |
| GET    | `/final_timetable`           | timetable    | View last generated timetable        |
| GET    | `/modify_timetable`          | timetable    | Manual timetable editor              |
| GET    | `/view_timetable`            | timetable    | Public timetable viewer (by username)|
| GET    | `/get_timetable`             | timetable    | JSON: timetable for a class/semester |
| GET    | `/api/schools`               | timetable    | JSON: all schools (public)           |
| GET    | `/api/classes`               | timetable    | JSON: classes for a school           |
| GET    | `/api/semesters`             | timetable    | JSON: semesters for class            |
| GET    | `/faculty_timetable`         | faculty      | Faculty timetable viewer page        |
| GET    | `/api/faculty_timetable`     | faculty      | JSON: timetable grid for teacher     |
| GET    | `/api/faculty_workload`      | faculty      | JSON: workload analytics for teacher |
| GET    | `/api/all_teachers`          | faculty      | JSON: all teachers for school        |
| GET    | `/login`                     | auth         | Login page                           |
| POST   | `/login`                     | auth         | Authenticate                         |
| GET    | `/register`                  | auth         | Register page                        |
| POST   | `/register`                  | auth         | Create account                       |
| GET    | `/logout`                    | auth         | Clear session                        |
| POST   | `/delete_account`            | auth         | Delete all institution data          |

---

## Timetable Generation Flow

```
POST /generate
  │
  └── perform_timetable_generation(class_name, semester, priorities, school_id)
        │
        ├── 1. Lookup class_id, course_id from DB
        ├── 2. Fetch timeslots → build id_to_time_map
        ├── 3. Fetch subjects → build credits_map, subject_faculty_map
        ├── 4. Compute lecture timeslots from school time_config
        ├── 5. Sync timeslots to DB (insert any new ones)
        │
        ├── [CRITICAL FIX]
        ├── 6. Read ALL timetable rows from DB (BEFORE any delete)
        │      → This is the fix for the DELETE-before-READ bug
        │
        ├── 7. Build faculty_busy_for_generation: {teacher_id: {(day,time),...}}
        │      → Only includes OTHER classes' entries (not the one being generated)
        │
        ├── 8. DELETE timetable rows only for target class_id
        │
        ├── 9. Build invalid_slots: {subject: set_of_break_slots}
        │      → Break slots are excluded for all subjects
        │      → Faculty conflicts handled separately via faculty_busy_slots
        │
        ├── 10. Fetch blocked/holiday days
        │
        ├── 11. Call genetic_algorithm()
        │       → receives faculty_busy_slots (cross-class occupancy)
        │       → receives subject_faculty_map
        │       → decode() checks faculty_busy before every assignment
        │       → decode() updates local_faculty_busy as it assigns
        │       → each chromosome evaluation uses deepcopy(faculty_busy_slots)
        │       → returns (schedule, unscheduled_list)
        │
        ├── 12. validate_teacher_conflicts(schedule, subject_faculty_map)
        │       → If any conflict found: rollback + return error
        │
        ├── 13. validate_class_conflicts(schedule)
        │       → If any slot collision: rollback + return error
        │
        └── 14. INSERT valid schedule rows → commit
              Return (saved_timetable, unscheduled_list, None)
```

---

## Faculty Constraint Logic

### Why conflicts were happening (before the fix):

The original `timetable_service.py` had this order:
```python
cursor.execute("DELETE FROM timetable WHERE class_id = %s", class_id)  # BUG: deletes first
db.commit()
cursor.execute("SELECT teacher_id, time_id, day FROM timetable")        # then reads — now empty!
```

This made `teacher_busy_map` always empty, so the GA had no cross-class constraints.

### How conflicts are prevented now:

1. **Read before delete** — All existing timetable rows are fetched BEFORE the delete statement.
2. **faculty_busy_for_generation** — Built from other-class rows only (excluding the class being regenerated).
3. **deepcopy in GA** — Each chromosome evaluation gets `deepcopy(faculty_busy_slots)` so evaluations are independent and don't corrupt each other.
4. **Hard reject in decode()** — If `(day, time) in local_faculty_busy[teacher_id]`, the slot is skipped entirely — not penalised, not assigned.
5. **Pre-commit validation** — `validate_teacher_conflicts()` runs before `db.commit()`. If it detects any conflict (which should be impossible after steps 1-4), it rolls back.

### Data flow for faculty constraints:

```
DB timetable (other classes)
    ↓ query (step 6)
faculty_busy_for_generation = {teacher_id: {(day,time), ...}}
    ↓ passed to genetic_algorithm()
    ↓ deepcopy per chromosome in calculate_fitness()
local_faculty_busy (per chromosome decode)
    ↓ checked before each slot assignment in decode()
    ↓ updated after each successful assignment
    → faculty conflicts are impossible within a decode run
```

---

## Holiday Logic

Holidays are stored in `school_holidays(school_id, day_name)`.

- Created on first visit to `/manage_timings` via `CREATE TABLE IF NOT EXISTS`.
- Stored per school, day name (e.g. "Saturday", "Wednesday").
- Loaded during generation as `blocked_days` list.
- Passed to `genetic_algorithm()` which excludes them from `available_days`.
- Also cached in `session['holiday_days']` for fast access.

---

## Validation Layer

Both validators run in `timetable_service.py` before `db.commit()`:

### `validate_teacher_conflicts(schedule, subject_faculty_map)`
- Builds `{teacher_id: {(day,time): subject}}` from proposed schedule.
- If any teacher appears twice at same (day,time): returns `(False, [conflict descriptions])`.
- On failure: caller does `db.rollback()` and returns error to client.

### `validate_class_conflicts(schedule)`
- Builds `{(day,time): subject}` from proposed schedule.
- If any slot appears twice within the class: returns `(False, [conflict descriptions])`.
- On failure: same rollback flow.

---

## Faculty Timetable Module

### Routes:
- `GET /faculty_timetable` — Page with faculty dropdown, timetable grid, workload card
- `GET /api/faculty_timetable?teacher_id=X` — JSON grid: `{Day_Time: {subject, class_name, semester, display}}`
- `GET /api/faculty_workload?teacher_id=X` — JSON: `{teacher_name, total_lectures, subjects: [...]}`
- `GET /api/all_teachers` — JSON: `[{teacher_id, teacher_name}]`

### Timetable grid cell format:
```json
{
  "subject": "Deep Learning",
  "class_name": "AI&DS",
  "semester": 7,
  "display": "Deep Learning | AI&DS | Sem 7"
}
```

---

## Generation Report System

After each generation, a report is stored in `session['generation_report']`:

```json
{
  "status": "success | partial",
  "class_name": "AI&DS",
  "semester": 7,
  "scheduled_count": 18,
  "unscheduled_count": 2,
  "unscheduled": [
    {
      "subject": "Deep Learning",
      "faculty": "Dr. Rajesh Sharma",
      "semester": 7,
      "class": "AI&DS",
      "reason": "No conflict-free slot available after applying faculty and timetable constraints"
    }
  ]
}
```

The report modal is shown immediately after generation in `generate.html`:
- ✅ Full schedule: green modal with lecture count
- ⚠️ Partial: amber modal with unscheduled table + Download Report button

---

## UI Architecture

- **Base layout:** `layout.html` — sidebar, topbar, flash messages, footer
- **Theme:** CSS variables with light/dark toggle (stored in `localStorage`)
- **Sidebar:** responsive — collapses to overlay on mobile (`< 768px`); iOS scroll-lock support
- **Timetable cards:** `subject-block` CSS class with 6 color variants (sb-blue, sb-ind, sb-grn, sb-gold, sb-red, sb-cyan)
- **Print support:** all pages have `@media print` blocks hiding nav/buttons
- **Fonts:** Inter + Outfit (Google Fonts)
- **Icons:** Font Awesome 6.4.0

---

## Session Variables

| Key                  | Type    | Purpose                                      |
|----------------------|---------|----------------------------------------------|
| `school_id`          | int     | Logged-in school's ID                        |
| `school_name`        | str     | Display name                                 |
| `time_config`        | dict    | `{start_time, end_time, lecture_duration, break_start, break_duration}` |
| `holiday_days`       | list    | List of day name strings (cache of DB)        |
| `timetable`          | list    | Last generated timetable entry list           |
| `generation_context` | dict    | `{class_name, semester, priorities}` for regeneration |
| `generation_report`  | dict    | Last generation report for modal display      |

---

## Known Decisions (Why, not What)

### Why session-based report (not DB table)?
Generation reports are ephemeral. They're only relevant immediately after generation. Adding a `generation_reports` table would require migrations, additional queries, and cleanup logic for no user-visible benefit. Session is appropriate here — it's tied to the user's browser session and automatically expires.

### Why deepcopy per chromosome evaluation?
Without deepcopy, all chromosomes in a generation share the same `faculty_busy_slots` dict. As one chromosome's `decode()` modifies it, subsequent chromosomes see corrupted state. This would make faculty constraints accumulate incorrectly across evaluations, destroying GA correctness.

### Why return (schedule, unscheduled) instead of schedule|None?
Returning `None` on infeasibility forces callers to retry or show an error. Returning a partial schedule allows the system to save what IS valid, report what isn't, and let the admin see the timetable and decide — which is far better UX than "generation failed."

### Why not a DB UNIQUE constraint on (teacher_id, time_id, day)?
A UNIQUE constraint would be the ultimate safety net, but it requires a schema migration that could break existing deployments. The application-level validation layer (`validate_teacher_conflicts`) provides equivalent safety and rolls back on failure, without requiring DB changes.

### Why is `subject_name` VARCHAR(20) in the DB?
Legacy schema decision. Long subject names will be silently truncated. If needed, run: `ALTER TABLE subject MODIFY subject_name VARCHAR(100);`

---

## Future Improvements

1. **Practical sessions** — The `practical` table exists but the GA doesn't schedule practicals yet. This is a significant feature gap.
2. **Room assignment** — No room allocation is implemented. All lectures are unroomed.
3. **DB UNIQUE constraint** — `ALTER TABLE timetable ADD UNIQUE KEY uq_teacher_slot (teacher_id, time_id, day);` for database-level safety net.
4. **Progressive Web App** — Add a service worker for offline schedule viewing.
5. **Export to Excel/PDF** — Currently only browser print. A proper PDF export via WeasyPrint or pdfkit would be more reliable.
6. **Conflict report email** — Send unscheduled lecture reports to admin email.
7. **Timetable versioning** — Allow saving multiple timetable versions and comparing them.
8. **Multi-room support** — Assign specific rooms per lecture slot.
