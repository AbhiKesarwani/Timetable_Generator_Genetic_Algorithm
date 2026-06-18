# 🕵️ Mission: Connect the Logic!

Welcome, Developer! Your mission is to bridge the gap between our **Python Codebase** and the **SQL Database**. 

Instead of just looking at the answers, follow this step-by-step guide to discover how the "brain" (Python) and the "memory" (SQL) work together.

---

## 🚀 Step 1: The Investigation
Open your **[`practice_queries.sql`](file:///c:/Users/djadh/Downloads/Timetable/practice_queries.sql)** file. You'll see several sections numbered 1 to 5. These are the "Memory Patterns" our app uses.

## 🚀 Step 2: The Logic Hunt
Now, open the following Python files. In each file, try to find a line that looks like `db.execute(...)` or `cursor.execute(...)`. 

Match each **File Discovery** with its **SQL Memory Pattern**:

### 🔍 Discovery A: `src/routes/main.py`
Inside the `dashboard()` function, the app counts classes, staff, and timetables.
*   **Question**: Which **Section** in the SQL file provides these counts?

### 🔍 Discovery B: `src/database/database.py`
Look for a function called `get_timetable_by_class()`. It uses a massive query with many `JOIN` keywords.
*   **Question**: Which **Section** in the SQL file contains this "Master Join"?

### 🔍 Discovery C: `src/routes/timetable.py`
Look at the `/api/schools` and `/api/classes` routes. They populate the dropdowns for the students.
*   **Question**: Which **Section** handles fetching the lists of schools and classes?

### 🔍 Discovery D: `src/auth/auth.py`
Inside the `login()` function, the app searches for a school using a `username`.
*   **Question**: Which **Section** shows how we find a school's private ID?

### 🔍 Discovery E: `src/routes/management.py`
Look for the code that runs when an Admin clicks "Add Teacher".
*   **Question**: Which **Section** performs the `INSERT` operation for new faculty?

---

## 🚀 Step 3: The Challenge
Once you think you've matched them all, ask yourself:
> **"Why do all these queries need a `school_id`?"**

(Hint: Think about what would happen if a student from School A accidentally saw the teachers from School B!)

---

## 🏁 Final Check
Are you feeling confident in your matches? 

👉 **[Go to the Solution Page to see if you are correct!](  Timetable/documentation/exercises/exercise_solutions.md)**
