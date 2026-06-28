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


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC Routes — No login required (read-only, mirrors student View Timetable)
# ─────────────────────────────────────────────────────────────────────────────

@faculty_bp.route('/view-faculty-timetable')
def public_faculty_timetable_page():
    """Public faculty timetable viewer — no authentication required."""
    return render_template('view_faculty_timetable.html')


@faculty_bp.route('/api/public/teachers')
def public_get_teachers():
    """
    Returns a list of teacher names for a given school username.
    Public endpoint — never exposes teacher_id or school_id.

    Query params:
      username (str) — institution admin username
    """
    username = request.args.get('username', '').strip()
    if not username:
        return jsonify({"error": "username is required"}), 400

    try:
        db = connect_db()
        cursor = db.cursor(dictionary=True)

        # Resolve school_id from username
        cursor.execute(
            "SELECT school_id FROM schools WHERE username = %s",
            (username,)
        )
        school_row = cursor.fetchone()
        if not school_row:
            db.close()
            return jsonify({"error": "Institution not found"}), 404

        school_id = school_row['school_id']

        # Return teacher names only — no IDs exposed
        cursor.execute(
            """
            SELECT DISTINCT t.teacher_name
            FROM teacher t
            JOIN timetable tt ON tt.teacher_id = t.teacher_id
            WHERE t.school_id = %s
            ORDER BY t.teacher_name
            """,
            (school_id,)
        )
        teachers = [row['teacher_name'] for row in cursor.fetchall()]
        db.close()
        return jsonify(teachers)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@faculty_bp.route('/api/public/faculty_timetable')
def public_get_faculty_timetable():
    """
    Returns timetable grid data for a named teacher at a given institution.
    Public endpoint — school_id resolved internally, never sent to client.

    Query params:
      username     (str) — institution admin username
      teacher_name (str) — exact teacher name
    """
    username = request.args.get('username', '').strip()
    teacher_name = request.args.get('teacher_name', '').strip()

    if not username or not teacher_name:
        return jsonify({"error": "username and teacher_name are required"}), 400

    try:
        db = connect_db()
        cursor = db.cursor(dictionary=True)

        # Resolve school from username
        cursor.execute(
            "SELECT school_id FROM schools WHERE username = %s",
            (username,)
        )
        school_row = cursor.fetchone()
        if not school_row:
            db.close()
            return jsonify({"error": "Institution not found"}), 404

        school_id = school_row['school_id']

        # Resolve teacher_id by name within this school (use first match)
        cursor.execute(
            "SELECT teacher_id FROM teacher WHERE teacher_name = %s AND school_id = %s LIMIT 1",
            (teacher_name, school_id)
        )
        teacher_row = cursor.fetchone()
        if not teacher_row:
            db.close()
            return jsonify({"error": "Faculty member not found"}), 404

        teacher_id = teacher_row['teacher_id']

        # Fetch timetable entries
        query = """
            SELECT
                s.subject_name,
                c.class_name,
                s.semester,
                tt.day,
                ts.timeslot
            FROM timetable tt
            JOIN subject   s  ON tt.subject_id  = s.subject_id
            JOIN class     c  ON tt.class_id    = c.class_id
            JOIN timeslot  ts ON tt.time_id     = ts.time_id
            WHERE tt.teacher_id = %s AND tt.school_id = %s
            ORDER BY tt.day, ts.timeslot
        """
        cursor.execute(query, (teacher_id, school_id))
        rows = cursor.fetchall()

        # Fetch school time config for visual_slots
        cursor.execute(
            "SELECT start_time, end_time, lecture_duration, break_start_time, break_duration "
            "FROM schools WHERE school_id = %s",
            (school_id,)
        )
        school_cfg = cursor.fetchone()
        db.close()

        # Build timetable dict
        timetable_dict = {}
        for row in rows:
            timeslot_val = row['timeslot']
            if isinstance(timeslot_val, timedelta):
                ts_sec = int(timeslot_val.total_seconds())
                timeslot_str = f"{ts_sec//3600:02}:{(ts_sec%3600)//60:02}:{ts_sec%60:02}"
            else:
                timeslot_str = str(timeslot_val)
                if len(timeslot_str) == 7:
                    timeslot_str = "0" + timeslot_str

            key = f"{row['day']}_{timeslot_str}"
            timetable_dict[key] = {
                "subject":    row['subject_name'],
                "class_name": row['class_name'],
                "semester":   row['semester'],
                "display":    f"{row['subject_name']} | {row['class_name']} | Sem {row['semester']}"
            }

        # Build visual_slots from school config
        def fmt_td(td):
            if not td:
                return None
            if not isinstance(td, timedelta):
                return str(td)
            sec = int(td.total_seconds())
            return f"{sec//3600:02}:{(sec%3600)//60:02}:{sec%60:02}"

        visual_slots = []
        if school_cfg:
            time_config = {
                'start_time':        fmt_td(school_cfg['start_time']),
                'end_time':          fmt_td(school_cfg['end_time']),
                'lecture_duration':  school_cfg['lecture_duration'],
                'break_start':       fmt_td(school_cfg['break_start_time']),
                'break_duration':    school_cfg['break_duration'],
            }
            visual_slots = get_daily_slots(time_config, include_break=True)

        if not visual_slots:
            # Fallback: derive from timetable keys
            slot_times = sorted(set(k.split('_')[1] for k in timetable_dict))
            visual_slots = [{'time': t, 'type': 'lecture'} for t in slot_times]

        return jsonify({
            "teacher_name": teacher_name,
            "timetable":    timetable_dict,
            "visual_slots": visual_slots,
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
