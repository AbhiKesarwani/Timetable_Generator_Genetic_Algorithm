from datetime import datetime, timedelta
import logging
from src.database.database import connect_db
from src.logic.algorithms import genetic_algorithm
from flask import session

def get_daily_slots(config, include_break=False):
    """Generates a list of timeslots based on school configuration."""
    start_str = config.get('start_time')
    end_str = config.get('end_time')
    duration_min = int(config.get('lecture_duration', 60))
    break_start_str = config.get('break_start')
    break_duration_min = int(config.get('break_duration', 0))

    def parse_time(t_str):
        if not t_str: return None
        if len(t_str.split(':')) == 3:
            return datetime.strptime(t_str, "%H:%M:%S")
        return datetime.strptime(t_str, "%H:%M")

    start_time = parse_time(start_str)
    end_time = parse_time(end_str)
    
    break_start = None
    break_end = None
    if break_start_str:
        break_start = parse_time(break_start_str)
        if break_start:
            break_end = break_start + timedelta(minutes=break_duration_min)

    slots = []
    current = start_time
    
    while current + timedelta(minutes=duration_min) <= end_time:
        slot_end = current + timedelta(minutes=duration_min)
        
        if break_start and break_end:
            if current >= break_start and current < break_end:
                 if include_break:
                     slots.append({'time': current.strftime("%H:%M:%S"), 'type': 'break'})
                 current = break_end 
                 continue
            
            if current < break_start and slot_end > break_start:
                 current = break_end
                 continue

        if include_break:
             slots.append({'time': current.strftime("%H:%M:%S"), 'type': 'lecture'})
        else:
             slots.append(current.strftime("%H:%M:%S"))
             
        current = slot_end
        
    return slots

def perform_timetable_generation(class_name, semester, priorities, school_id):
    """
    Helper function to perform the actual timetable generation logic.
    Returns: (saved_timetable, error_message)
    """
    try:
        db = connect_db()
        cursor = db.cursor(dictionary=True)

        # 1. Get IDs for Class and Course
        cursor.execute("SELECT class_id FROM class WHERE class_name = %s AND school_id = %s", (class_name, school_id))
        res = cursor.fetchone()
        if not res:
            db.close()
            return None, f"Class '{class_name}' not found."
        class_id = res['class_id']

        cursor.execute("SELECT course_id FROM course WHERE school_id = %s LIMIT 1", (school_id,))
        course_res = cursor.fetchone()
        course_id = course_res['course_id'] if course_res else 1

        # 2. Map Subject -> Teacher -> Busy Slots
        invalid_slots = {} 
        cursor.execute("SELECT time_id, timeslot FROM timeslot")
        all_db_slots = cursor.fetchall()
        
        id_to_time_map = {}
        for row in all_db_slots:
            t_str = str(row['timeslot'])
            if len(t_str) == 7: 
                 t_str = "0" + t_str
            id_to_time_map[row['time_id']] = t_str

        # 3. Subject Data
        cursor.execute("SELECT subject_name, credits, teacher_id FROM subject WHERE class_id = %s AND semester = %s AND school_id = %s", (class_id, semester, school_id))
        subject_rows = cursor.fetchall()
        
        subjects = [row['subject_name'] for row in subject_rows]
        credits_map = {row['subject_name']: row['credits'] for row in subject_rows}
        
        final_priorities = {}
        for sub in subjects:
            final_priorities[sub] = int(priorities.get(sub, 1))

        # 4. Time Config
        time_config = session.get('time_config')
        if not time_config:
             db.close()
             return None, "Time configuration not found. Please re-login."

        all_slots_with_metadata = get_daily_slots(time_config, include_break=True)
        timeslots = [s['time'] for s in all_slots_with_metadata]
        break_slots = [s['time'] for s in all_slots_with_metadata if s['type'] == 'break']
        
        # 5. Sync Timeslots
        timeslot_id_map = {} 
        for slot in timeslots:
             found_id = None
             for tid, tstr in id_to_time_map.items():
                 if tstr == slot:
                     found_id = tid
                     break
            
             if found_id:
                 timeslot_id_map[slot] = found_id
             else:
                 cursor.execute("INSERT INTO timeslot (timeslot, type_of_class) VALUES (%s, 'lecture')", (slot,))
                 timeslot_id_map[slot] = cursor.lastrowid
                 id_to_time_map[cursor.lastrowid] = slot
        
        db.commit()

        # 6. Teacher Busy Constraints
        cursor.execute("DELETE FROM timetable WHERE class_id = %s", (class_id,))
        db.commit()

        cursor.execute("SELECT teacher_id, time_id, day FROM timetable")
        existing_schedule_rows = cursor.fetchall()
        
        teacher_busy_map = {}
        for r_tid, r_timeid, r_day in existing_schedule_rows:
            if r_tid not in teacher_busy_map:
                teacher_busy_map[r_tid] = set()
            t_str = id_to_time_map.get(r_timeid)
            if t_str and r_day:
                teacher_busy_map[r_tid].add((r_day, t_str))

        days_list = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        for row in subject_rows:
            subj_name = row['subject_name']
            if subj_name not in invalid_slots:
                invalid_slots[subj_name] = set()
            t_id = row['teacher_id']
            if t_id in teacher_busy_map:
                invalid_slots[subj_name].update(teacher_busy_map[t_id])
            for day in days_list:
                for b_slot in break_slots:
                    invalid_slots[subj_name].add((day, b_slot))

        # 7. Algorithm Call
        timetable_result = genetic_algorithm(subjects, timeslots, final_priorities, credits_map, invalid_slots=invalid_slots)

        for entry in timetable_result:
            if isinstance(entry["timeslot"], timedelta):  
                total_seconds = int(entry["timeslot"].total_seconds())
                h, m, s = total_seconds // 3600, (total_seconds % 3600) // 60, total_seconds % 60
                entry["timeslot"] = f"{h:02}:{m:02}:{s:02}"

        # 8. Save Results
        saved_timetable = [] 
        for entry in timetable_result:
            semester_int = int(semester)
            cursor.execute(
                "SELECT subject_id, teacher_id FROM subject WHERE subject_name = %s AND class_id = %s AND semester = %s",
                (entry["subject"], class_id, semester_int)
            )
            result = cursor.fetchone()
            if result:
                subject_id = result['subject_id']
                teacher_id = result['teacher_id']
                time_id = timeslot_id_map.get(entry["timeslot"])
                
                if not time_id:
                    cursor.execute("SELECT time_id FROM timeslot WHERE timeslot = %s", (entry["timeslot"],))
                    time_id_result = cursor.fetchone()
                    if time_id_result:
                         time_id = int(time_id_result['time_id'])
                
                if not time_id: continue 
                
                try:
                    cursor.execute(
                        "INSERT INTO timetable (teacher_id, subject_id, class_id, course_id, time_id, day, school_id) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                        (teacher_id, subject_id, class_id, course_id, time_id, entry['day'], school_id)
                    )
                    saved_timetable.append(entry)
                except Exception as e:
                    logging.error(f"Insert Failed: {e}")
        
        db.commit()
        cursor.close()
        db.close()
        return saved_timetable, None

    except Exception as e:
        import traceback
        traceback.print_exc()
        return None, str(e)
