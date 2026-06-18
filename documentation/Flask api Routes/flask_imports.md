# Flask Imports Documentation

This document lists all the modules and functions imported from the `flask` library across the project, along with their usage context.

## Core Flask Components

### `Flask`
Used to create the main application instance.
- [app.py](file:///c:/Users/djadh/Downloads/Projects/timetablegenrator/app.py)

### `Blueprint`
Used to organize the application into distinct components (routes).
- [src/auth/auth.py](file:///c:/Users/djadh/Downloads/Projects/timetablegenrator/src/auth/auth.py)
- [src/routes/generation.py](file:///c:/Users/djadh/Downloads/Projects/timetablegenrator/src/routes/generation.py)
- [src/routes/main.py](file:///c:/Users/djadh/Downloads/Projects/timetablegenrator/src/routes/main.py)
- [src/routes/management.py](file:///c:/Users/djadh/Downloads/Projects/timetablegenrator/src/routes/management.py)
- [src/routes/timetable.py](file:///c:/Users/djadh/Downloads/Projects/timetablegenrator/src/routes/timetable.py)

---

## Request & Response Handling

### `request`
Used to access incoming request data (form data, JSON, query parameters).
- [src/auth/auth.py](file:///c:/Users/djadh/Downloads/Projects/timetablegenrator/src/auth/auth.py)
- [src/routes/generation.py](file:///c:/Users/djadh/Downloads/Projects/timetablegenrator/src/routes/generation.py)
- [src/routes/management.py](file:///c:/Users/djadh/Downloads/Projects/timetablegenrator/src/routes/management.py)
- [src/routes/timetable.py](file:///c:/Users/djadh/Downloads/Projects/timetablegenrator/src/routes/timetable.py)

### `render_template`
Used to render HTML templates.
- [src/auth/auth.py](file:///c:/Users/djadh/Downloads/Projects/timetablegenrator/src/auth/auth.py)
- [src/routes/generation.py](file:///c:/Users/djadh/Downloads/Projects/timetablegenrator/src/routes/generation.py)
- [src/routes/main.py](file:///c:/Users/djadh/Downloads/Projects/timetablegenrator/src/routes/main.py)
- [src/routes/management.py](file:///c:/Users/djadh/Downloads/Projects/timetablegenrator/src/routes/management.py)
- [src/routes/timetable.py](file:///c:/Users/djadh/Downloads/Projects/timetablegenrator/src/routes/timetable.py)

### `jsonify`
Used to return JSON responses from API routes.
- [src/routes/generation.py](file:///c:/Users/djadh/Downloads/Projects/timetablegenrator/src/routes/generation.py)
- [src/routes/timetable.py](file:///c:/Users/djadh/Downloads/Projects/timetablegenrator/src/routes/timetable.py)

---

## Navigation & User Feedback

### `redirect` & `url_for`
Used for handling HTTP redirects and generating URLs for defined routes.
- [src/auth/auth.py](file:///c:/Users/djadh/Downloads/Projects/timetablegenrator/src/auth/auth.py)
- [src/routes/generation.py](file:///c:/Users/djadh/Downloads/Projects/timetablegenrator/src/routes/generation.py)
- [src/routes/management.py](file:///c:/Users/djadh/Downloads/Projects/timetablegenrator/src/routes/management.py)
- [src/utils/decorators.py](file:///c:/Users/djadh/Downloads/Projects/timetablegenrator/src/utils/decorators.py)

### `flash`
Used to display temporary messages to the user (success, error, info).
- [src/auth/auth.py](file:///c:/Users/djadh/Downloads/Projects/timetablegenrator/src/auth/auth.py)
- [src/routes/generation.py](file:///c:/Users/djadh/Downloads/Projects/timetablegenrator/src/routes/generation.py)
- [src/routes/management.py](file:///c:/Users/djadh/Downloads/Projects/timetablegenrator/src/routes/management.py)

---

## State Management

### `session`
Used to store user-specific information across requests.
- [src/auth/auth.py](file:///c:/Users/djadh/Downloads/Projects/timetablegenrator/src/auth/auth.py)
- [src/routes/generation.py](file:///c:/Users/djadh/Downloads/Projects/timetablegenrator/src/routes/generation.py)
- [src/routes/main.py](file:///c:/Users/djadh/Downloads/Projects/timetablegenrator/src/routes/main.py)
- [src/routes/management.py](file:///c:/Users/djadh/Downloads/Projects/timetablegenrator/src/routes/management.py)
- [src/routes/timetable.py](file:///c:/Users/djadh/Downloads/Projects/timetablegenrator/src/routes/timetable.py)
- [src/services/timetable_service.py](file:///c:/Users/djadh/Downloads/Projects/timetablegenrator/src/services/timetable_service.py)
- [src/utils/decorators.py](file:///c:/Users/djadh/Downloads/Projects/timetablegenrator/src/utils/decorators.py)
