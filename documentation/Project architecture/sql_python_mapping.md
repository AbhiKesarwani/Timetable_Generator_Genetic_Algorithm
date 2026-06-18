# Python Logic to SQL Mapping 🔗

This document maps the Python modules and routes to the specific SQL queries found in [`practice_queries.sql`](file:///c:/Users/djadh/Downloads/Timetable/practice_queries.sql). Use this as a guide to understand how the backend interacts with the database.

## Mapping Overview

| Application Feature | Python File | SQL Section | Purpose |
| :--- | :--- | :--- | :--- |
| **Authentication** | [`src/auth/auth.py`](file:///c:/Users/djadh/Downloads/Timetable/src/auth/auth.py) | **1.1** | Fetching school ID during login. |
| **Public School List** | [`src/routes/timetable.py`](file:///c:/Users/djadh/Downloads/Timetable/src/routes/timetable.py) | **1.2** | Populating the School dropdown for students. |
| **Admin Dashboard** | [`src/routes/main.py`](file:///c:/Users/djadh/Downloads/Timetable/src/routes/main.py) | **Section 2** | Calculating real-time stats (Classes, Staff, Timetables). |
| **Teacher Management** | [`src/routes/management.py`](file:///c:/Users/djadh/Downloads/Timetable/src/routes/management.py) | **3.1** | Adding/Deleting faculty members. |
| **Generation Wizard** | [`src/routes/generation.py`](file:///c:/Users/djadh/Downloads/Timetable/src/routes/generation.py) | **3.2** | Fetching subjects to begin the generation process. |
| **School Config** | [`src/routes/management.py`](file:///c:/Users/djadh/Downloads/Timetable/src/routes/management.py) | **3.3** | Updating institutional timings and break hours. |
| **Timetable Rendering** | [`src/database/database.py`](file:///c:/Users/djadh/Downloads/Timetable/src/database/database.py) | **Section 4** | The "Master Join" query that pulls everything together. |
| **Dynamic Filtering** | [`src/routes/timetable.py`](file:///c:/Users/djadh/Downloads/Timetable/src/routes/timetable.py) | **Section 5** | Powering the dependent dropdowns (School -> Class -> Sem). |

---

## Why This Matters

1.  **Isolation**: Notice how almost every query in the Python files includes `WHERE school_id = %s`. This matches the isolation principle explained in **Section 1** of the SQL script.
2.  **Performance**: The "Master Join" in **Section 4** is executed inside `get_timetable_by_class()` to avoid multiple database round-trips.
3.  **Validation**: The queries in **Section 5** ensure that the frontend only displays data that actually exists in the database, preventing "404 Not Found" errors for students.
