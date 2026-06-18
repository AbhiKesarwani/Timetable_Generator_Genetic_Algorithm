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

        saved_timetable, error = perform_timetable_generation(class_name, semester, priorities, school_id)
        if error:
            return jsonify({"error": error}), 500

        session['timetable'] = saved_timetable
        session['generation_context'] = {
            'class_name': class_name,
            'semester': semester,
            'priorities': priorities 
        }
        return jsonify({"message": "Timetable generated successfully!", "redirect": url_for('timetable_view.final_timetable')})
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
    
    saved_timetable, error = perform_timetable_generation(class_name, semester, priorities, school_id)
    if error:
        flash(f"Regeneration failed: {error}", "error")
        return redirect(url_for('timetable_view.final_timetable'))
        
    session['timetable'] = saved_timetable
    flash("Timetable regenerated successfully!", "success")
    return redirect(url_for('timetable_view.final_timetable'))
