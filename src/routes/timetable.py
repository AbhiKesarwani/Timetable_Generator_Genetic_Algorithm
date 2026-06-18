from flask import Blueprint, render_template, request, jsonify, session
from datetime import timedelta
from src.database.database import connect_db, get_timetable_by_class
from src.services.timetable_service import get_daily_slots
from src.utils.decorators import login_required

timetable_bp = Blueprint('timetable_view', __name__)

@timetable_bp.route('/save_modified_timetable', methods=['POST'])
@login_required
def save_modified_timetable():
    try:
        data = request.json
        updated_timetable = data.get('timetable')
        if not updated_timetable:
            return jsonify({"error": "Timetable data is missing"}), 400
        session['timetable'] = updated_timetable 
        return jsonify({"message": "Timetable updated successfully!", "redirect": url_for('timetable_view.final_timetable')})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@timetable_bp.route('/final_timetable')
@login_required
def final_timetable():
    timetable_data = session.get('timetable', [])
    context = session.get('generation_context', {})
    structured_timetable = {}
    for entry in timetable_data:
        day = entry['day']
        timeslot = entry['timeslot']
        subject = entry['subject']
        structured_timetable[(day, timeslot)] = subject

    time_config = session.get('time_config')
    if time_config:
        visual_slots = get_daily_slots(time_config, include_break=True)
    else:
        visual_slots = [{'time': slot, 'type': 'lecture'} for slot in sorted(set(entry['timeslot'] for entry in timetable_data))]

    return render_template("final_timetable.html", 
                           timetable=structured_timetable, 
                           timeslots=visual_slots,
                           class_name=context.get('class_name'),
                           semester=context.get('semester'))

@timetable_bp.route('/modify_timetable', methods=['GET', 'POST'])
@login_required
def modify_timetable():
    if request.method == 'GET':
        timetable = session.get('timetable', [])
        db = connect_db()
        cursor = db.cursor()
        cursor.execute("SELECT timeslot FROM timeslot")
        timeslots = [str(row[0]) for row in cursor.fetchall()]
        db.close()
        return render_template("modify_timetable.html", timetable=timetable, timeslots=timeslots)
    elif request.method == 'POST':
        try:
            data = request.json
            updated_timetable = data.get('timetable')
            if not updated_timetable:
                return jsonify({"error": "Timetable data is missing"}), 400
            session['timetable'] = updated_timetable  
            return jsonify({"message": "Timetable updated successfully!", "redirect": url_for('timetable_view.final_timetable')})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        
@timetable_bp.route('/view_timetable')
def view_timetable():
    return render_template("view_timetable.html")

@timetable_bp.route('/get_timetable', methods=['GET'])
def get_timetable():
    try:
        class_name = request.args.get('class_name')
        semester = request.args.get('semester')
        school_username = request.args.get('username')
        school_id = None
        
        if school_username:
             db = connect_db()
             cursor = db.cursor(dictionary=True)
             cursor.execute("SELECT school_id FROM schools WHERE username = %s", (school_username,))
             school = cursor.fetchone()
             db.close()
             if school:
                 school_id = school['school_id']
             else:
                 return jsonify({"error": "School not found. Please check the username."}), 404
        
        if not school_id:
            school_id = session.get('school_id')
        if not school_id:
            return jsonify({"error": "Please provide the School's Admin Username."}), 400
        if not class_name or not semester:
            return jsonify({"error": "Missing class name or semester"}), 400

        timetable_db, timeslots_list = get_timetable_by_class(class_name, semester, school_id)
        visual_slots = []
        time_config = session.get('time_config')
        
        if not time_config and school_id:
             db = connect_db()
             cursor = db.cursor(dictionary=True)
             cursor.execute("SELECT * FROM schools WHERE school_id = %s", (school_id,))
             school_config = cursor.fetchone()
             db.close()
             if school_config:
                 def fmt_td(td):
                     if not td: return None
                     if not isinstance(td, timedelta): return str(td)
                     ts = int(td.total_seconds())
                     return f"{ts//3600:02}:{(ts%3600)//60:02}:{ts%60:02}"
                 time_config = {
                    'start_time': fmt_td(school_config['start_time']),
                    'end_time': fmt_td(school_config['end_time']),
                    'lecture_duration': school_config['lecture_duration'],
                    'break_start': fmt_td(school_config['break_start_time']),
                    'break_duration': school_config['break_duration']
                 }

        if time_config:
             visual_slots = get_daily_slots(time_config, include_break=True)
        else:
             visual_slots = [{'time': t, 'type': 'lecture'} for t in timeslots_list]

        if timetable_db:
             return jsonify({"timetable": timetable_db, "visual_slots": visual_slots})

        timetable_data = session.get('timetable', [])
        if not timetable_data:
            return jsonify({"error": "No timetable found for this class."}), 404

        structured_timetable = {}
        for entry in timetable_data:
            day = entry['day']
            timeslot = entry['timeslot']
            subject = entry['subject']
            structured_timetable[f"{day}_{timeslot}"] = subject
        return jsonify({"timetable": structured_timetable, "visual_slots": visual_slots})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@timetable_bp.route('/api/schools')
def get_schools():
    try:
        db = connect_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT username, school_name FROM schools")
        schools = cursor.fetchall()
        db.close()
        return jsonify(schools)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@timetable_bp.route('/api/classes')
def get_classes():
    try:
        username = request.args.get('username')
        if not username:
            return jsonify({"error": "Username is required"}), 400
            
        db = connect_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT DISTINCT c.class_name 
            FROM class c
            JOIN schools s ON c.school_id = s.school_id
            JOIN timetable t ON c.class_id = t.class_id
            WHERE s.username = %s
        """, (username,))
        classes = [row['class_name'] for row in cursor.fetchall()]
        db.close()
        return jsonify(classes)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@timetable_bp.route('/api/semesters')
def get_semesters():
    try:
        username = request.args.get('username')
        class_name = request.args.get('class_name')
        if not username or not class_name:
            return jsonify({"error": "Username and Class Name are required"}), 400
            
        db = connect_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT DISTINCT sub.semester 
            FROM subject sub
            JOIN class c ON sub.class_id = c.class_id
            JOIN schools s ON c.school_id = s.school_id
            JOIN timetable t ON t.subject_id = sub.subject_id
            WHERE s.username = %s AND c.class_name = %s AND t.class_id = c.class_id
        """, (username, class_name))
        semesters = [row['semester'] for row in cursor.fetchall()]
        db.close()
        return jsonify(sorted(semesters))
    except Exception as e:
        return jsonify({"error": str(e)}), 500
