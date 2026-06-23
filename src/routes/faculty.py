"""
Faculty Timetable Module
========================
Routes:
  GET /faculty_timetable              — Render the faculty timetable page
  GET /api/faculty_timetable          — JSON: timetable grid for a teacher
  GET /api/faculty_workload           — JSON: workload analytics for a teacher
  GET /api/all_teachers               — JSON: list of all teachers for this school
"""

from flask import Blueprint, render_template, request, jsonify, session
from datetime import timedelta
from src.database.database import connect_db
from src.services.timetable_service import get_daily_slots
from src.utils.decorators import login_required

faculty_bp = Blueprint('faculty', __name__)


# ─────────────────────────────────────────────────────────────────────────────
# Page Route
# ─────────────────────────────────────────────────────────────────────────────

@faculty_bp.route('/faculty_timetable')
@login_required
def faculty_timetable_page():
    """Render the faculty timetable viewer page."""
    school_id = session['school_id']
    db = connect_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        "SELECT teacher_id, teacher_name FROM teacher WHERE school_id = %s ORDER BY teacher_name",
        (school_id,)
    )
    teachers = cursor.fetchall()
    db.close()
    return render_template('faculty_timetable.html', teachers=teachers)


# ─────────────────────────────────────────────────────────────────────────────
# API: All Teachers (for dropdown)
# ─────────────────────────────────────────────────────────────────────────────

@faculty_bp.route('/api/all_teachers')
@login_required
def get_all_teachers():
    school_id = session['school_id']
    try:
        db = connect_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            "SELECT teacher_id, teacher_name FROM teacher WHERE school_id = %s ORDER BY teacher_name",
            (school_id,)
        )
        teachers = cursor.fetchall()
        db.close()
        return jsonify(teachers)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# API: Faculty Timetable Grid
# ─────────────────────────────────────────────────────────────────────────────

@faculty_bp.route('/api/faculty_timetable')
@login_required
def get_faculty_timetable():
    """
    Returns timetable grid data for a specific teacher.

    Query params:
      teacher_id (int) — required

    Response:
      {
        "teacher_name": str,
        "timetable": { "Monday_08:00:00": "Mathematics-I | AI&DS | Sem 1", ... },
        "visual_slots": [{"time": "08:00:00", "type": "lecture"}, ...]
      }
    """
    school_id = session['school_id']
    teacher_id = request.args.get('teacher_id', type=int)

    if not teacher_id:
        return jsonify({"error": "teacher_id is required"}), 400

    try:
        db = connect_db()
        cursor = db.cursor(dictionary=True)

        # Get teacher name
        cursor.execute(
            "SELECT teacher_name FROM teacher WHERE teacher_id = %s AND school_id = %s",
            (teacher_id, school_id)
        )
        teacher_row = cursor.fetchone()
        if not teacher_row:
            db.close()
            return jsonify({"error": "Teacher not found"}), 404
        teacher_name = teacher_row['teacher_name']

        # Fetch all timetable entries for this teacher
        query = """
            SELECT
                s.subject_name,
                c.class_name,
                s.semester,
                tt.day,
                ts.timeslot
            FROM timetable tt
            JOIN subject s  ON tt.subject_id  = s.subject_id
            JOIN class   c  ON tt.class_id    = c.class_id
            JOIN timeslot ts ON tt.time_id    = ts.time_id
            WHERE tt.teacher_id = %s AND tt.school_id = %s
            ORDER BY tt.day, ts.timeslot
        """
        cursor.execute(query, (teacher_id, school_id))
        rows = cursor.fetchall()
        db.close()

        # Build timetable dict: key = "Day_HH:MM:SS", value = display string
        timetable_dict = {}
        for row in rows:
            timeslot_val = row['timeslot']
            if isinstance(timeslot_val, timedelta):
                ts = int(timeslot_val.total_seconds())
                timeslot_str = f"{ts//3600:02}:{(ts%3600)//60:02}:{ts%60:02}"
            else:
                timeslot_str = str(timeslot_val)
                if len(timeslot_str) == 7:
                    timeslot_str = "0" + timeslot_str

            key = f"{row['day']}_{timeslot_str}"
            timetable_dict[key] = {
                "subject": row['subject_name'],
                "class_name": row['class_name'],
                "semester": row['semester'],
                "display": f"{row['subject_name']} | {row['class_name']} | Sem {row['semester']}"
            }

        # Get visual slots for the time grid
        time_config = session.get('time_config')
        if time_config:
            visual_slots = get_daily_slots(time_config, include_break=True)
        else:
            # Fallback: derive from timetable entries
            slot_times = sorted(set(
                v.split('_')[1] if '_' in k else k
                for k, v in timetable_dict.items()
            ))
            visual_slots = [{'time': t, 'type': 'lecture'} for t in slot_times]

        return jsonify({
            "teacher_name": teacher_name,
            "timetable": timetable_dict,
            "visual_slots": visual_slots
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# API: Faculty Workload Analytics
# ─────────────────────────────────────────────────────────────────────────────

@faculty_bp.route('/api/faculty_workload')
@login_required
def get_faculty_workload():
    """
    Returns workload analytics for a specific teacher.

    Query params:
      teacher_id (int) — required

    Response:
      {
        "teacher_name": str,
        "total_lectures": int,
        "subjects": [
          {
            "subject_name": str,
            "class_name": str,
            "semester": int,
            "lecture_count": int
          },
          ...
        ]
      }
    """
    school_id = session['school_id']
    teacher_id = request.args.get('teacher_id', type=int)

    if not teacher_id:
        return jsonify({"error": "teacher_id is required"}), 400

    try:
        db = connect_db()
        cursor = db.cursor(dictionary=True)

        # Get teacher name
        cursor.execute(
            "SELECT teacher_name FROM teacher WHERE teacher_id = %s AND school_id = %s",
            (teacher_id, school_id)
        )
        teacher_row = cursor.fetchone()
        if not teacher_row:
            db.close()
            return jsonify({"error": "Teacher not found"}), 404
        teacher_name = teacher_row['teacher_name']

        # Aggregate lectures by subject + class + semester
        query = """
            SELECT
                s.subject_name,
                c.class_name,
                s.semester,
                COUNT(tt.timetable_id) AS lecture_count
            FROM timetable tt
            JOIN subject s ON tt.subject_id = s.subject_id
            JOIN class   c ON tt.class_id   = c.class_id
            WHERE tt.teacher_id = %s AND tt.school_id = %s
            GROUP BY s.subject_name, c.class_name, s.semester
            ORDER BY s.semester, s.subject_name
        """
        cursor.execute(query, (teacher_id, school_id))
        subject_rows = cursor.fetchall()
        db.close()

        total_lectures = sum(r['lecture_count'] for r in subject_rows)

        return jsonify({
            "teacher_name": teacher_name,
            "total_lectures": total_lectures,
            "subjects": [
                {
                    "subject_name": r['subject_name'],
                    "class_name": r['class_name'],
                    "semester": r['semester'],
                    "lecture_count": r['lecture_count']
                }
                for r in subject_rows
            ]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
