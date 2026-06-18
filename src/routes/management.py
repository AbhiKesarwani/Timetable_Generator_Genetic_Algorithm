from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from datetime import datetime, timedelta
from src.database.database import connect_db
from src.utils.decorators import login_required

management_bp = Blueprint('management', __name__)

@management_bp.route('/manage_teachers', methods=['GET', 'POST'])
@login_required
def manage_teachers():
    db = connect_db()
    cursor = db.cursor(dictionary=True)
    edit_teacher = None
    
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'delete':
            teacher_id = request.form.get('teacher_id')
            try:
                cursor.execute("DELETE FROM timetable WHERE teacher_id = %s AND school_id = %s", (teacher_id, session['school_id']))
                cursor.execute("DELETE FROM allocated_timeslots WHERE teacher_id = %s AND school_id = %s", (teacher_id, session['school_id']))
                cursor.execute("DELETE FROM subject WHERE teacher_id = %s AND school_id = %s", (teacher_id, session['school_id']))
                cursor.execute("DELETE FROM teacher WHERE teacher_id = %s AND school_id = %s", (teacher_id, session['school_id']))
                db.commit()
                flash('Teacher and their assigned subjects deleted successfully!', 'success')
            except Exception as e:
                flash(f'Error deleting teacher: {str(e)}', 'error')
        elif action == 'update':
            teacher_id = request.form.get('teacher_id')
            name = request.form.get('teacher_name')
            try:
                cursor.execute("UPDATE teacher SET teacher_name = %s WHERE teacher_id = %s AND school_id = %s", (name, teacher_id, session['school_id']))
                db.commit()
                flash('Teacher updated successfully!', 'success')
                return redirect(url_for('management.manage_teachers'))
            except Exception as e:
                flash(f'Error updating teacher: {str(e)}', 'error')
        else:
            try:
                name = request.form.get('teacher_name')
                if name:
                    cursor.execute("INSERT INTO teacher (teacher_name, school_id) VALUES (%s, %s)", (name, session['school_id']))
                    db.commit()
                    flash('Teacher added successfully!', 'success')
            except Exception as e:
                flash(f'Error adding teacher: {str(e)}', 'error')

    edit_id = request.args.get('edit_id')
    if edit_id:
        cursor.execute("SELECT * FROM teacher WHERE teacher_id = %s AND school_id = %s", (edit_id, session['school_id']))
        edit_teacher = cursor.fetchone()
            
    cursor.execute("SELECT * FROM teacher WHERE school_id = %s", (session['school_id'],))
    teachers = cursor.fetchall()
    db.close()
    return render_template('manage_teachers.html', teachers=teachers, edit_teacher=edit_teacher)

@management_bp.route('/manage_subjects', methods=['GET', 'POST'])
@login_required
def manage_subjects():
    db = connect_db()
    cursor = db.cursor(dictionary=True)
    school_id = session['school_id']

    cursor.execute("SELECT course_id FROM course WHERE school_id = %s LIMIT 1", (school_id,))
    course = cursor.fetchone()
    if not course:
        cursor.execute("INSERT INTO course (course_name, school_id) VALUES ('Standard', %s)", (school_id,))
        db.commit()
        course_id = cursor.lastrowid
    else:
        course_id = course['course_id']
        
    edit_class = None
    edit_subject = None

    if request.method == 'POST':
        action = request.form.get('action')
        try:
            if action == 'add_class':
                class_name = request.form.get('class_name')
                if class_name:
                    cursor.execute("INSERT INTO class (class_name, school_id) VALUES (%s, %s)", (class_name, school_id))
                    db.commit()
                    flash('Class added successfully!', 'success')
            elif action == 'update_class':
                class_id = request.form.get('class_id')
                class_name = request.form.get('class_name')
                cursor.execute("UPDATE class SET class_name = %s WHERE class_id = %s AND school_id = %s", (class_name, class_id, school_id))
                db.commit()
                flash('Class updated successfully!', 'success')
                return redirect(url_for('management.manage_subjects'))
            elif action == 'delete_class':
                class_id = request.form.get('class_id')
                cursor.execute("DELETE FROM subject WHERE class_id = %s AND school_id = %s", (class_id, school_id))
                cursor.execute("DELETE FROM class WHERE class_id = %s AND school_id = %s", (class_id, school_id))
                db.commit()
                flash('Class and its subjects deleted successfully!', 'success')
            elif action == 'add_subject':
                subject_name = request.form.get('subject_name')
                class_id = request.form.get('class_id')
                teacher_id = request.form.get('teacher_id')
                credits = request.form.get('credits') 
                semester = request.form.get('semester')
                cursor.execute("""
                    INSERT INTO subject (subject_name, class_id, course_id, teacher_id, semester, credits, school_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (subject_name, class_id, course_id, teacher_id, semester, credits, school_id))
                db.commit()
                flash('Subject added successfully!', 'success')
            elif action == 'update_subject':
                subject_id = request.form.get('subject_id')
                subject_name = request.form.get('subject_name')
                class_id = request.form.get('class_id')
                teacher_id = request.form.get('teacher_id')
                credits = request.form.get('credits') 
                semester = request.form.get('semester')
                cursor.execute("""
                    UPDATE subject SET subject_name=%s, class_id=%s, teacher_id=%s, semester=%s, credits=%s
                    WHERE subject_id=%s AND school_id=%s
                """, (subject_name, class_id, teacher_id, semester, credits, subject_id, school_id))
                db.commit()
                flash('Subject updated successfully!', 'success')
                return redirect(url_for('management.manage_subjects'))
            elif action == 'delete_subject':
                subject_id = request.form.get('subject_id')
                cursor.execute("DELETE FROM subject WHERE subject_id = %s AND school_id = %s", (subject_id, school_id))
                db.commit()
                flash('Subject deleted successfully!', 'success')
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')

    edit_class_id = request.args.get('edit_class_id')
    if edit_class_id:
        cursor.execute("SELECT * FROM class WHERE class_id = %s AND school_id = %s", (edit_class_id, school_id))
        edit_class = cursor.fetchone()
    edit_subject_id = request.args.get('edit_subject_id')
    if edit_subject_id:
         cursor.execute("SELECT * FROM subject WHERE subject_id = %s AND school_id = %s", (edit_subject_id, school_id))
         edit_subject = cursor.fetchone()

    cursor.execute("SELECT * FROM class WHERE school_id = %s", (school_id,))
    classes = cursor.fetchall()
    cursor.execute("SELECT * FROM teacher WHERE school_id = %s", (school_id,))
    teachers = cursor.fetchall()
    cursor.execute("""
        SELECT s.*, c.class_name, t.teacher_name 
        FROM subject s
        JOIN class c ON s.class_id = c.class_id
        JOIN teacher t ON s.teacher_id = t.teacher_id
        WHERE s.school_id = %s
    """, (school_id,))
    subjects = cursor.fetchall()
    db.close()
    return render_template('manage_subjects.html', classes=classes, teachers=teachers, subjects=subjects, edit_class=edit_class, edit_subject=edit_subject)

@management_bp.route('/manage_timings', methods=['GET', 'POST'])
@login_required
def manage_timings():
    if request.method == 'POST':
        start_time_str = request.form.get('start_time')
        lecture_duration = int(request.form.get('lecture_duration'))
        num_lectures = int(request.form.get('num_lectures'))
        break_after = int(request.form.get('break_after'))
        break_duration = int(request.form.get('break_duration') or 0)

        start_time = datetime.strptime(start_time_str, "%H:%M")
        break_start_time = None
        break_start_str = None
        if break_after > 0:
            break_start_time = start_time + timedelta(minutes=break_after * lecture_duration)
            break_start_str = break_start_time.strftime("%H:%M")
        
        total_minutes = num_lectures * lecture_duration
        if break_after > 0 and break_after < num_lectures:
             total_minutes += break_duration
        end_time = start_time + timedelta(minutes=total_minutes)
        end_time_str = end_time.strftime("%H:%M")

        db = connect_db()
        cursor = db.cursor()
        try:
            sql = """
                UPDATE schools SET start_time = %s, end_time = %s, lecture_duration = %s, break_start_time = %s, break_duration = %s
                WHERE school_id = %s
            """
            cursor.execute(sql, (start_time_str, end_time_str, lecture_duration, break_start_str, break_duration, session['school_id']))
            db.commit()
            session['time_config'] = {
                'start_time': start_time_str, 'end_time': end_time_str, 'lecture_duration': lecture_duration,
                'break_start': break_start_str, 'break_duration': break_duration,
                'num_lectures': num_lectures, 'break_after': break_after
            }
            flash('Timings updated successfully!', 'success')
        except Exception as e:
            flash(f'Error updating timings: {str(e)}', 'error')
        finally:
            db.close()
        return redirect(url_for('management.manage_timings'))

    config = session.get('time_config')
    if config and 'num_lectures' not in config:
        try:
            s_time = datetime.strptime(config.get('start_time'), "%H:%M")
            e_time = datetime.strptime(config.get('end_time'), "%H:%M")
            l_dur = int(config.get('lecture_duration', 60))
            b_dur = int(config.get('break_duration', 0))
            b_start_str = config.get('break_start')
            total_duration = (e_time - s_time).seconds / 60
            if b_start_str:
                b_start = datetime.strptime(b_start_str, "%H:%M")
                lectures_before = (b_start - s_time).seconds / 60 / l_dur
                b_end = b_start + timedelta(minutes=b_dur)
                lectures_after = (e_time - b_end).seconds / 60 / l_dur
                config['num_lectures'] = int(lectures_before + lectures_after)
                config['break_after'] = int(lectures_before)
            else:
                config['num_lectures'] = int(total_duration / l_dur)
                config['break_after'] = 0
        except Exception: pass
    return render_template('manage_timings.html', config=config)
