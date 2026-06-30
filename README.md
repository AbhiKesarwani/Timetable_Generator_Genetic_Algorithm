# 🎓 AI-Powered Academic Timetable Generator

An intelligent web-based timetable generation system for **Schools, Colleges, and Universities** that automatically creates conflict-free academic timetables using a **Genetic Algorithm**.

The system minimizes manual scheduling effort by considering faculty availability, subject credits, institutional working hours, holidays, and existing timetables while preventing faculty conflicts across multiple semesters.

## 🌐 Live Demo

🚀 **Application:** https://timetable-generator-genetic-algorit.vercel.app/

---

# ✨ Features

### 🏫 Institution Management

- Multi-institution support
- Secure administrator authentication
- Institution-wise timetable isolation

### 👨‍🏫 Faculty Management

- Add, edit and delete faculty members
- Assign faculty to subjects
- Faculty workload management

### 📚 Curriculum Management

- Create semester-wise subjects
- Credit-based lecture allocation
- Faculty-subject mapping
- Edit/Delete curriculum

### ⚙️ Schedule Configuration

Configure:

- Institution working hours
- Lecture duration
- Break timing
- Break duration
- Weekly holidays
- Sunday permanently blocked

---

# 🤖 AI Timetable Generator

The scheduling engine automatically generates optimized timetables while satisfying institutional constraints.

It considers:

- Faculty availability
- Existing published timetables
- Subject credit requirements
- Working hours
- Break periods
- Holiday constraints
- Cross-semester faculty scheduling

The generator avoids timetable conflicts and produces the most feasible timetable possible.

---

# 🚫 Faculty Conflict Prevention

One of the major challenges in timetable generation is preventing a faculty member from being scheduled in multiple classrooms simultaneously.

This project solves that problem by checking **every newly generated timetable against all existing institutional timetables**.

If a faculty member is already occupied at a particular day and time, that slot becomes unavailable during timetable generation.

Example:

Dr. Rajesh Sharma teaches

- Mathematics-I (Semester 1)
- Data Structures (Semester 3)
- Machine Learning (Semester 5)

The system guarantees that these lectures are never scheduled at the same time.

---

# 📅 Holiday-aware Scheduling

Administrators can configure weekly holidays.

Examples:

- Tuesday holiday
- Tuesday + Wednesday holidays
- Saturday working or non-working
- Sunday permanently blocked

The Genetic Algorithm automatically excludes blocked days while generating timetables.

---

# ⚠️ Intelligent Handling of Impossible Schedules

If sufficient time slots are unavailable due to constraints such as:

- Holidays
- Faculty availability
- Credit requirements

the system:

- Generates every feasible lecture
- Skips only impossible lectures
- Reports the unscheduled lectures with reasons

Instead of creating conflicting timetables, the application prioritizes correctness.

---

# 👨‍🎓 Public Student Timetable

Students can view published timetables without logging in.

Simply select:

- Institution
- Batch
- Semester

and the timetable is displayed instantly.

---

# 👨‍🏫 Public Faculty Timetable

Faculty members can also access their teaching schedule without logging in.

Select:

- Institution
- Faculty Member

and the weekly teaching timetable is displayed.

---

# 🗂 Existing Timetable Management

Administrators can:

- View existing published timetables
- Delete individual semester timetables
- Regenerate timetables

Deleting a timetable removes only timetable records.

Faculty, subjects, batches and configuration remain unchanged.

---

# 🧠 Genetic Algorithm

The scheduling engine is based on a Genetic Algorithm approach for solving the timetable optimization problem. Genetic Algorithms are widely used for educational timetabling because they efficiently search large solution spaces while satisfying hard scheduling constraints. :contentReference[oaicite:0]{index=0}

The algorithm follows these stages:

1. Initial Population
2. Fitness Evaluation
3. Selection
4. Crossover
5. Mutation
6. New Population
7. Best Schedule Selection

Fitness is calculated using scheduling constraints such as:

- Faculty conflicts
- Holiday constraints
- Existing timetable conflicts
- Credit distribution
- Lecture allocation

---

# 🖥 Tech Stack

### Backend

- Python
- Flask
- Jinja2
- MySQL

### Frontend

- HTML5
- CSS3
- JavaScript
- Responsive UI

### Algorithm

- Genetic Algorithm

---

# 📱 Responsive Design

The application is fully responsive and optimized for

- Desktop
- Laptop
- Tablet
- Mobile

---

# 📂 Project Structure

```
├── frontend/
│   ├── static/
│   └── templates/
│
├── src/
│   ├── auth/
│   ├── database/
│   ├── logic/
│   ├── routes/
│   ├── services/
│   └── utils/
│
├── SQL_Queries/
├── app.py
├── requirements.txt
└── README.md
```

---

# 🚀 Getting Started

## Clone the repository

```bash
git clone https://github.com/AbhiKesarwani/Timetable_Generator_Genetic_Algorithm.git
cd Timetable_Generator_Genetic_Algorithm
```

## Create virtual environment

```bash
python -m venv venv
```

### Windows

```bash
venv\Scripts\activate
```

### Linux / macOS

```bash
source venv/bin/activate
```

## Install dependencies

```bash
pip install -r requirements.txt
```

## Configure Database

Create a MySQL database and execute the SQL scripts provided in the **SQL_Queries** folder.

Update your database credentials in the configuration file.

## Run

```bash
python app.py
```

Application will be available at

```
http://127.0.0.1:5000
```

---

# 🎯 Future Improvements

- Room allocation optimization
- Laboratory scheduling
- PDF/Excel export
- Faculty workload analytics
- Multi-department scheduling
- AI-assisted schedule recommendations

---

# 👨‍💻 Developer

**Abhinav Kesarwani**

B.Tech — Artificial Intelligence & Data Science

Gati Shakti Vishwavidyalaya

GitHub: https://github.com/AbhiKesarwani

LinkedIn: https://www.linkedin.com/in/abhinav-kesarwani/

---

# ⭐ If you found this project useful

Please consider giving the repository a **Star ⭐**

It motivates further development and improvements.