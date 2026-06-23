from datetime import datetime, timedelta
import logging
from copy import deepcopy
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


# ═════════════════════════════════════════════════════════════════════════════
# VALIDATION LAYER
# Both functions run BEFORE committing to the database.
# ═════════════════════════════════════════════════════════════════════════════

def validate_teacher_conflicts(schedule, subject_faculty_map):
    """
    Verify that no teacher appears twice at the same (day, time) in the schedule
    about to be committed.

    Args:
        schedule           : list of {"subject": str, "day": str, "timeslot": str}
        subject_faculty_map: dict {subject_name: teacher_id}

    Returns:
        (is_valid: bool, conflicts: list of str descriptions)
    """
    teacher_slot_map = {}  # {teacher_id: {(day, time): subject}}
    conflicts = []

    for entry in schedule:
        subj = entry["subject"]
        day = entry["day"]
        time = entry["timeslot"]
        teacher_id = subject_faculty_map.get(subj)

        if teacher_id is None:
            continue  # No teacher assigned — skip

        key = (day, time)
        if teacher_id not in teacher_slot_map:
            teacher_slot_map[teacher_id] = {}

        if key in teacher_slot_map[teacher_id]:
            conflicts.append(
                f"Teacher ID {teacher_id} has TWO lectures at {day} {time}: "
                f"'{teacher_slot_map[teacher_id][key]}' and '{subj}'"
            )
        else:
            teacher_slot_map[teacher_id][key] = subj

    return (len(conflicts) == 0), conflicts


def validate_class_conflicts(schedule):
    """
    Verify that no class slot (day, time) appears twice in the schedule.

    Args:
        schedule: list of {"subject": str, "day": str, "timeslot": str}

    Returns:
        (is_valid: bool, conflicts: list of str descriptions)
    """
    slot_map = {}   # {(day, time): subject}
    conflicts = []

    for entry in schedule:
        key = (entry["day"], entry["timeslot"])
        if key in slot_map:
            conflicts.append(
                f"Class slot conflict at {entry['day']} {entry['timeslot']}: "
                f"'{slot_map[key]}' and '{entry['subject']}'"
            )
        else:
            slot_map[key] = entry["subject"]

    return (len(conflicts) == 0), conflicts


# ═════════════════════════════════════════════════════════════════════════════
# MAIN GENERATION FUNCTION
# ═════════════════════════════════════════════════════════════════════════════

def perform_timetable_generation(class_name, semester, priorities, school_id):
    """
    Perform faculty-conflict-safe timetable generation.

    Fixed order (Bug 1 fix):
      STEP 1  Read ALL timetable rows from DB (before any delete)
      STEP 2  Build global_faculty_busy_map  {teacher_id: set of (day, time)}
      STEP 3  Build class_busy_map           {class_id:   set of (day, time)}
      STEP 4  Construct invalid_slots and faculty_busy_slots for the GA
      STEP 5  DELETE only the target class's timetable rows
      STEP 6  Run genetic_algorithm() with faculty-aware parameters
      STEP 7  validate_teacher_conflicts()  — rollback if fails
      STEP 8  validate_class_conflicts()    — rollback if fails
      STEP 9  Insert results and commit

    Returns:
        (saved_timetable, unscheduled_list, error_message)
        saved_timetable  : list of successfully saved entry dicts
        unscheduled_list : list of {"subject": str, "reason": str} for unscheduled
        error_message    : str if fatal error, else None
    """
    db = None
    try:
        db = connect_db()
        cursor = db.cursor(dictionary=True)

        # ── 1. Get IDs for Class and Course ──────────────────────────────────
        cursor.execute(
            "SELECT class_id FROM class WHERE class_name = %s AND school_id = %s",
            (class_name, school_id)
        )
        res = cursor.fetchone()
        if not res:
            db.close()
            return None, [], f"Class '{class_name}' not found."
        class_id = res['class_id']

        cursor.execute(
            "SELECT course_id FROM course WHERE school_id = %s LIMIT 1",
            (school_id,)
        )
        course_res = cursor.fetchone()
        course_id = course_res['course_id'] if course_res else 1

        # ── 2. Build Timeslot ID Map ──────────────────────────────────────────
        cursor.execute("SELECT time_id, timeslot FROM timeslot")
        all_db_slots = cursor.fetchall()

        id_to_time_map = {}
        for row in all_db_slots:
            t_str = str(row['timeslot'])
            if len(t_str) == 7:
                t_str = "0" + t_str
            id_to_time_map[row['time_id']] = t_str

        # ── 3. Fetch Subject Data ─────────────────────────────────────────────
        cursor.execute(
            "SELECT subject_name, credits, teacher_id FROM subject "
            "WHERE class_id = %s AND semester = %s AND school_id = %s",
            (class_id, semester, school_id)
        )
        subject_rows = cursor.fetchall()

        subjects = [row['subject_name'] for row in subject_rows]
        credits_map = {row['subject_name']: row['credits'] for row in subject_rows}

        # subject_faculty_map: needed by algorithm AND validation layer
        subject_faculty_map = {
            row['subject_name']: row['teacher_id']
            for row in subject_rows
            if row['teacher_id'] is not None
        }

        final_priorities = {}
        for sub in subjects:
            final_priorities[sub] = int(priorities.get(sub, 1))

        # ── 4. Time Config ────────────────────────────────────────────────────
        time_config = session.get('time_config')
        if not time_config:
            db.close()
            return None, [], "Time configuration not found. Please re-login."

        all_slots_with_metadata = get_daily_slots(time_config, include_break=True)
        timeslots = [s['time'] for s in all_slots_with_metadata if s['type'] == 'lecture']
        break_slots = [s['time'] for s in all_slots_with_metadata if s['type'] == 'break']

        # ── 5. Sync Timeslots into DB ─────────────────────────────────────────
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
                cursor.execute(
                    "INSERT INTO timeslot (timeslot, type_of_class) VALUES (%s, 'lecture')",
                    (slot,)
                )
                new_id = cursor.lastrowid
                timeslot_id_map[slot] = new_id
                id_to_time_map[new_id] = slot

        db.commit()

        # ── 6. CRITICAL FIX: Read ALL timetable rows BEFORE deleting ─────────
        # This preserves cross-class faculty occupancy information.
        # The old code deleted FIRST then read — making teacher_busy_map always empty.
        cursor.execute(
            "SELECT teacher_id, time_id, day FROM timetable WHERE school_id = %s",
            (school_id,)
        )
        existing_schedule_rows = cursor.fetchall()

        # Build global faculty busy map from ALL existing timetable entries
        # (including other classes and semesters)
        global_faculty_busy_slots = {}  # {teacher_id: set of (day, time_str)}
        for row in existing_schedule_rows:
            t_id = row['teacher_id']
            t_str = id_to_time_map.get(row['time_id'])
            r_day = row['day']
            if t_str and r_day and t_id:
                if t_id not in global_faculty_busy_slots:
                    global_faculty_busy_slots[t_id] = set()
                global_faculty_busy_slots[t_id].add((r_day, t_str))

        # ── 7. NOW delete only the target class's rows ────────────────────────
        cursor.execute("DELETE FROM timetable WHERE class_id = %s", (class_id,))
        db.commit()

        # After deletion, remove this class's existing entries from the faculty
        # busy map so we only block cross-class slots, not the class we're regenerating.
        # We do this by re-reading the remaining timetable (after deletion).
        # Actually simpler: re-query the timetable excluding this class_id.
        cursor.execute(
            "SELECT teacher_id, time_id, day FROM timetable "
            "WHERE school_id = %s AND class_id != %s",
            (school_id, class_id)
        )
        other_class_rows = cursor.fetchall()

        faculty_busy_for_generation = {}  # {teacher_id: set of (day, time_str)}
        for row in other_class_rows:
            t_id = row['teacher_id']
            t_str = id_to_time_map.get(row['time_id'])
            r_day = row['day']
            if t_str and r_day and t_id:
                if t_id not in faculty_busy_for_generation:
                    faculty_busy_for_generation[t_id] = set()
                faculty_busy_for_generation[t_id].add((r_day, t_str))

        # ── 8. Build invalid_slots (break slots only now — faculty handled separately) ─
        days_list = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        invalid_slots = {}
        for row in subject_rows:
            subj_name = row['subject_name']
            if subj_name not in invalid_slots:
                invalid_slots[subj_name] = set()
            # Only add break slots here; faculty constraints go into faculty_busy_for_generation
            for day in days_list:
                for b_slot in break_slots:
                    invalid_slots[subj_name].add((day, b_slot))

        # ── 9. Fetch holiday/blocked days ────────────────────────────────────
        blocked_days = []
        try:
            cursor.execute(
                "SELECT day_name FROM school_holidays WHERE school_id = %s",
                (school_id,)
            )
            holiday_rows = cursor.fetchall()
            blocked_days = [row['day_name'] for row in holiday_rows]
        except Exception:
            blocked_days = session.get('holiday_days', [])

        # ── 10. Run Genetic Algorithm ─────────────────────────────────────────
        # faculty_busy_for_generation is passed as global pre-existing occupancy.
        # The GA will deepcopy() it per chromosome evaluation — global state is safe.
        timetable_result, unscheduled_list = genetic_algorithm(
            subjects,
            timeslots,
            final_priorities,
            credits_map,
            invalid_slots=invalid_slots,
            blocked_days=blocked_days,
            faculty_busy_slots=faculty_busy_for_generation,
            subject_faculty_map=subject_faculty_map,
        )

        # ── 11. Normalise timeslot format (timedelta → HH:MM:SS) ─────────────
        for entry in timetable_result:
            if isinstance(entry["timeslot"], timedelta):
                total_seconds = int(entry["timeslot"].total_seconds())
                h = total_seconds // 3600
                m = (total_seconds % 3600) // 60
                s = total_seconds % 60
                entry["timeslot"] = f"{h:02}:{m:02}:{s:02}"

        # ── 12. Pre-commit Validation ─────────────────────────────────────────
        teacher_ok, teacher_conflicts = validate_teacher_conflicts(
            timetable_result, subject_faculty_map
        )
        class_ok, class_conflicts = validate_class_conflicts(timetable_result)

        if not teacher_ok:
            logging.error("TEACHER CONFLICT DETECTED before commit — rolling back")
            for c in teacher_conflicts:
                logging.error(f"  {c}")
            db.rollback()
            return None, [], (
                "Internal validation failed: teacher conflicts detected. "
                "This should not happen — please report. Details: " +
                "; ".join(teacher_conflicts)
            )

        if not class_ok:
            logging.error("CLASS SLOT CONFLICT DETECTED before commit — rolling back")
            for c in class_conflicts:
                logging.error(f"  {c}")
            db.rollback()
            return None, [], (
                "Internal validation failed: class slot conflicts detected. "
                "Details: " + "; ".join(class_conflicts)
            )

        # ── 13. Save validated results ────────────────────────────────────────
        saved_timetable = []
        for entry in timetable_result:
            semester_int = int(semester)
            cursor.execute(
                "SELECT subject_id, teacher_id FROM subject "
                "WHERE subject_name = %s AND class_id = %s AND semester = %s",
                (entry["subject"], class_id, semester_int)
            )
            result = cursor.fetchone()
            if result:
                subject_id = result['subject_id']
                teacher_id = result['teacher_id']
                time_id = timeslot_id_map.get(entry["timeslot"])

                if not time_id:
                    cursor.execute(
                        "SELECT time_id FROM timeslot WHERE timeslot = %s",
                        (entry["timeslot"],)
                    )
                    time_id_result = cursor.fetchone()
                    if time_id_result:
                        time_id = int(time_id_result['time_id'])

                if not time_id:
                    logging.warning(f"No time_id found for timeslot {entry['timeslot']} — skipping")
                    continue

                try:
                    cursor.execute(
                        "INSERT INTO timetable "
                        "(teacher_id, subject_id, class_id, course_id, time_id, day, school_id) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                        (teacher_id, subject_id, class_id, course_id,
                         time_id, entry['day'], school_id)
                    )
                    saved_timetable.append(entry)
                except Exception as e:
                    logging.error(f"Insert Failed for {entry}: {e}")

        db.commit()
        cursor.close()
        db.close()

        # ── 14. Enrich unscheduled list with faculty name for report ──────────
        enriched_unscheduled = []
        for item in unscheduled_list:
            subj = item["subject"]
            t_id = subject_faculty_map.get(subj)
            enriched_unscheduled.append({
                "subject": subj,
                "teacher_id": t_id,
                "reason": item["reason"]
            })

        return saved_timetable, enriched_unscheduled, None

    except Exception as e:
        import traceback
        traceback.print_exc()
        if db:
            try:
                db.rollback()
            except Exception:
                pass
            try:
                db.close()
            except Exception:
                pass
        return None, [], str(e)
