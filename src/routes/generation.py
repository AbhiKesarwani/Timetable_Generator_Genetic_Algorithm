from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from src.database.database import connect_db, fetch_data
from src.utils.decorators import login_required
from src.services.timetable_service import perform_timetable_generation

generation_bp = Blueprint('generation', __name__)


@generation_bp.route('/credits')
@login_required
def credits_page():
    return render_template('credits_page_timeslot.html')


@generation_bp.route('/subjects', methods=['GET'])
@login_required
def get_subjects():
    class_name = request.args.get('class_name')
    semester = request.args.get('semester')
    subjects, _ = fetch_data(class_name, semester, session['school_id'])
    return jsonify(subjects)


@generation_bp.route('/save_priorities', methods=['POST'])
@login_required
def save_priorities():
    return jsonify({"success": True})


@generation_bp.route('/generate_setup')
@login_required
def generate_setup():
    db = connect_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM class WHERE school_id = %s", (session['school_id'],))
    classes = cursor.fetchall()
    db.close()
    return render_template('generate.html', classes=classes)


@generation_bp.route('/generate', methods=['POST'])
@login_required
def generate_timetable():
    try:
        data = request.json
        class_name = data.get('class_name')
        semester = data.get('semester')
        priorities = data.get('priorities', {})
        school_id = session['school_id']

        saved_timetable, unscheduled_list, error = perform_timetable_generation(
            class_name, semester, priorities, school_id
        )

        if error:
            return jsonify({"error": error}), 500

        session['timetable'] = saved_timetable
        session['generation_context'] = {
            'class_name': class_name,
            'semester': semester,
            'priorities': priorities
        }

        # Build generation report
        report = _build_report(saved_timetable, unscheduled_list, class_name, semester, school_id)
        session['generation_report'] = report

        return jsonify({
            "message": "Timetable generated successfully!",
            "redirect": url_for('timetable_view.final_timetable'),
            "report": report
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@generation_bp.route('/regenerate_quick')
@login_required
def regenerate_quick():
    context = session.get('generation_context')
    if not context:
        flash("No recent generation context found. Please generate normally first.", "warning")
        return redirect(url_for('generation.generate_setup'))

    class_name = context.get('class_name')
    semester = context.get('semester')
    priorities = context.get('priorities')
    school_id = session['school_id']

    saved_timetable, unscheduled_list, error = perform_timetable_generation(
        class_name, semester, priorities, school_id
    )

    if error:
        flash(f"Regeneration failed: {error}", "error")
        return redirect(url_for('timetable_view.final_timetable'))

    session['timetable'] = saved_timetable
    report = _build_report(saved_timetable, unscheduled_list, class_name, semester, school_id)
    session['generation_report'] = report

    if unscheduled_list:
        flash(
            f"Timetable regenerated with {len(unscheduled_list)} unscheduled lecture(s). "
            "Check the generation report for details.",
            "warning"
        )
    else:
        flash("Timetable regenerated successfully! All lectures scheduled.", "success")

    return redirect(url_for('timetable_view.final_timetable'))


def _build_report(saved_timetable, unscheduled_list, class_name, semester, school_id):
    """
    Build a generation report dict for display in the UI modal and session storage.
    Enriches unscheduled entries with teacher names from DB.
    """
    scheduled_count = len(saved_timetable)
    unscheduled_count = len(unscheduled_list)

    # Enrich with teacher names if teacher_id is present
    enriched_unscheduled = []
    if unscheduled_list:
        try:
            db = connect_db()
            cursor = db.cursor(dictionary=True)
            cursor.execute(
                "SELECT teacher_id, teacher_name FROM teacher WHERE school_id = %s",
                (school_id,)
            )
            teacher_map = {row['teacher_id']: row['teacher_name'] for row in cursor.fetchall()}
            db.close()
        except Exception:
            teacher_map = {}

        for item in unscheduled_list:
            t_id = item.get('teacher_id')
            enriched_unscheduled.append({
                "subject": item["subject"],
                "faculty": teacher_map.get(t_id, "Faculty Not Assigned") if t_id else "Faculty Not Assigned",
                "semester": semester,
                "class": class_name,
                "reason": item["reason"]
            })

    status = "success" if unscheduled_count == 0 else "partial"

    return {
        "status": status,
        "class_name": class_name,
        "semester": semester,
        "scheduled_count": scheduled_count,
        "unscheduled_count": unscheduled_count,
        "unscheduled": enriched_unscheduled,
    }
