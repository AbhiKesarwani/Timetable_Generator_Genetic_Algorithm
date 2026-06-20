-- practice_queries.sql
-- 🎓 Educational script to learn the SQL core of the Timetable Generator
-- Goal: Understand CRUD (Create, Read, Update, Delete) and Data Isolation

USE timetable_db;

-----------------------------------------------------------
-- SECTION 1: DATA ISOLATION (The Multi-Tenant Pattern)
-----------------------------------------------------------
-- In this app, multiple schools share the same tables.
-- Every query MUST filter by school_id (or school username) to ensure privacy.

-- 1.1 Find a school's ID from its username
SELECT school_id, school_name FROM schools WHERE username = 'test';

-- 1.2 Fetch all schools (Used for the Student Access dropdown)
SELECT username, school_name FROM schools;


-----------------------------------------------------------
-- SECTION 2: DASHBOARD STATISTICS (Aggregation)
-----------------------------------------------------------
-- These queries power the dynamic stats on the Admin Dashboard.
-- Set @sid = (your school_id) for these practice queries.
SET @sid = 1;

-- 2.1 Count total classes registered
SELECT COUNT(*) FROM class WHERE school_id = @sid;

-- 2.2 Count total staff (teachers)
SELECT COUNT(*) FROM teacher WHERE school_id = @sid;

-- 2.3 Count how many classes have a generated timetable
SELECT COUNT(DISTINCT class_id) FROM timetable WHERE school_id = @sid;


-----------------------------------------------------------
-- SECTION 3: MANAGEMENT MODULE (CRUD)
-----------------------------------------------------------

-- 3.1 Adding a new teacher
INSERT INTO teacher (teacher_name, school_id) VALUES ('New Professor', @sid);

-- 3.2 Fetching subjects assigned to a specific class for the "Wizard"
-- This is used in the frontend fetch call.
SELECT subject_name FROM subject 
WHERE class_id = (SELECT class_id FROM class WHERE class_name = 'BACKEND SY' AND school_id = @sid)
AND semester = 3 AND school_id = @sid;

-- 3.3 Updating school hours/timings
UPDATE schools 
SET start_time = '08:00', lecture_duration = 45 
WHERE school_id = @sid;


-----------------------------------------------------------
-- SECTION 4: THE MASTER JOIN (Timetable Retrieval)
-----------------------------------------------------------
-- This is the most important query in the app.
-- It combines 4 tables to show a human-readable schedule.

SELECT 
    s.subject_name, 
    t.day, 
    ts.timeslot,
    tc.teacher_name
FROM timetable t
JOIN subject s ON t.subject_id = s.subject_id
JOIN timeslot ts ON t.time_id = ts.time_id
JOIN teacher tc ON s.teacher_id = tc.teacher_id
JOIN class c ON t.class_id = c.class_id
WHERE c.class_name = 'FRONTEND FY' 
  AND s.semester = 1 
  AND t.school_id = @sid
ORDER BY FIELD(t.day, 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'), ts.timeslot;


-----------------------------------------------------------
-- SECTION 5: STUDENT ACCESS (Searching)
-----------------------------------------------------------

-- 5.1 Fetch classes that ONLY have generated timetables
-- Used to prevent students from selecting empty classes.
SELECT DISTINCT c.class_name 
FROM class c
JOIN timetable t ON c.class_id = t.class_id
WHERE c.school_id = @sid;

-- 5.2 Fetch valid semesters for a specific class
SELECT DISTINCT sub.semester 
FROM subject sub
JOIN timetable t ON t.subject_id = sub.subject_id
WHERE t.school_id = @sid AND sub.class_id = 3; -- Using class_id directly here

-----------------------------------------------------------
-- Practice Challenge: 
-- Can you write a query to find which teacher has the most lectures assigned across the whole week?
-----------------------------------------------------------
