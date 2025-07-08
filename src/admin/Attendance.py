from flask import Blueprint, request, jsonify
from src.DatabaseConnection import Database
from datetime import date,datetime
from collections import defaultdict
import traceback


db = Database()
attendance_bp = Blueprint('attendance_bp', __name__)
@attendance_bp.route('/get_attendance', methods=['GET'])
def get_attendance():
    campus_id = request.args.get('campusId', type=int)


    if campus_id is None:
        return jsonify({"success": False, "error": "Missing campus_id"}), 400

    try:
        today = date.today().strftime('%Y-%m-%d')

        # ---------- STUDENT ATTENDANCE ----------
        total_students_sql = "SELECT rfid FROM Students WHERE campusid = %s"
        student_rfids = [s['rfid'] for s in db.fetch_all(total_students_sql, (campus_id,))]

        present_students_sql = """
            SELECT rfid FROM General_Attendance
            WHERE DATE(date) = %s AND status = 'Present' AND rfid IN (
                SELECT rfid FROM Students WHERE campusid = %s
            )
        """
        on_leave_students_sql = """
            SELECT rfid FROM General_Attendance
            WHERE DATE(date) = %s AND status = 'Leave' AND rfid IN (
                SELECT rfid FROM Students WHERE campusid = %s
            )
        """

        present_students = {row['rfid'] for row in db.fetch_all(present_students_sql, (today, campus_id))}
        on_leave_students = {row['rfid'] for row in db.fetch_all(on_leave_students_sql, (today, campus_id))}
        total_students = len(student_rfids)

        absent_students = [
            rfid for rfid in student_rfids
            if rfid not in present_students and rfid not in on_leave_students
        ]

        student_data = {
            "total_students": total_students,
            "present_students": len(present_students),
            "on_leave_students": len(on_leave_students),
            "absent_students": len(absent_students),
            "present_percentage": round((len(present_students) / total_students) * 100, 2) if total_students else 0,
            "on_leave_percentage": round((len(on_leave_students) / total_students) * 100, 2) if total_students else 0,
            "absent_percentage": round((len(absent_students) / total_students) * 100, 2) if total_students else 0
        }

        # ---------- TEACHER ATTENDANCE ----------
        teacher_sql = """
            SELECT e.RFID FROM employee e
            WHERE e.CampusID = %s
        """
        teacher_rfids = [t['RFID'] for t in db.fetch_all(teacher_sql, (campus_id,))]

        teacher_attendance_sql = """
            SELECT RFID, Attendance_status FROM Employee_Attendance
            WHERE Attendance_date = %s AND RFID IN (
                SELECT RFID FROM employee WHERE CampusID = %s
            )
        """
        attendance_records = db.fetch_all(teacher_attendance_sql, (today, campus_id))

        present_teachers = sum(1 for t in attendance_records if t["Attendance_status"] == "Present")
        on_leave_teachers = sum(1 for t in attendance_records if t["Attendance_status"] == "Leave")
        absent_teachers = sum(1 for t in attendance_records if t["Attendance_status"] == "Absent")
        total_teachers = len(teacher_rfids)

        teacher_data = {
            "total_teachers": total_teachers,
            "present_teachers": present_teachers,
            "on_leave_teachers": on_leave_teachers,
            "absent_teachers": total_teachers-present_teachers-on_leave_teachers,
            "present_percentage": round((present_teachers / total_teachers) * 100, 2) if total_teachers else 0,
            "on_leave_percentage": round((on_leave_teachers / total_teachers) * 100, 2) if total_teachers else 0,
            "absent_percentage": round((absent_teachers / total_teachers) * 100, 2) if total_teachers else 0
        }

        return jsonify({
            "success": True,
            "student_data": student_data,
            "teacher_data": teacher_data
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500



@attendance_bp.route('/get_unmarked_attendees', methods=['GET'])
def get_unmarked_attendees():
    campus_id = request.args.get('campus_id', type=int)
    year = request.args.get('year', type=int)
    if campus_id is None or year is None:
        return jsonify({"success": False, "error": "Missing campus_id or year"}), 400
    try:
        today = date.today().strftime('%Y-%m-%d')
        if year == 0:
            unmarked_students_sql = """
                SELECT s.rfid, s.student_name 
                FROM Students s
                WHERE s.campusid = %s 
                AND s.year IN (1, 2) 
                AND s.rfid NOT IN (
                    SELECT DISTINCT ga.rfid FROM General_Attendance ga 
                    WHERE DATE(ga.date) = %s
                )
            """
            params = (campus_id, today)
        else:
            unmarked_students_sql = """
                SELECT s.rfid, s.student_name 
                FROM Students s
                WHERE s.campusid = %s 
                AND s.year = %s
                AND s.rfid NOT IN (
                    SELECT DISTINCT ga.rfid FROM General_Attendance ga 
                    WHERE DATE(ga.date) = %s
                )
            """
            params = (campus_id, year, today)
        unmarked_students = db.fetch_all(unmarked_students_sql, params)
        return jsonify({
            "success": True,
            "unmarked_students": unmarked_students
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@attendance_bp.route('/mark_present', methods=['POST'])
def mark_present():
    try:
        data = request.get_json()
        students = data.get("students", [])
        if not students:
            return jsonify({"success": False, "message": "No students received"}), 400

        today_date = date.today().strftime('%Y-%m-%d')
        current_time = datetime.now().strftime('%H:%M:%S')
        db_instance = Database()
        for student in students:
            rfid = student.get("rfid") if isinstance(student, dict) else student
            if not rfid:
                continue
            check_attendance_sql = """
                SELECT COUNT(*) FROM General_Attendance 
                WHERE date = %s AND RFID = %s
            """
            result = db_instance.fetch_one(check_attendance_sql, (today_date, rfid))
            if result and result['COUNT(*)'] > 0:
                continue
            update_students_sql = """
                UPDATE Students 
                SET DaysAttended = DaysAttended + 1, 
                    TotalDays = TotalDays + 1 
                WHERE RFID = %s
            """
            db_instance.execute_query(update_students_sql, (rfid,))
            insert_attendance_sql = """
                INSERT INTO General_Attendance (date, RFID, Status, time) 
                VALUES (%s, %s, %s, %s)
            """
            db_instance.execute_query(insert_attendance_sql, (today_date, rfid, "Present", current_time))
        return jsonify({"success": True, "message": "Attendance recorded successfully!"})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@attendance_bp.route('/get_attendance_data_view_attendance', methods=['GET'])
def get_attendance_data_view_attendance():
    campus_id = request.args.get('campus_id', type=int)

    if campus_id is None:
        return jsonify({"success": False, "error": "Missing campus_id"}), 400

    try:
        total_students_sql = "SELECT rfid, student_name FROM Students WHERE campusid = %s"
        students = db.fetch_all(total_students_sql, (campus_id,))

        today = date.today().strftime('%Y-%m-%d')
        present_students_sql = """
            SELECT DISTINCT ga.rfid 
            FROM General_Attendance ga
            JOIN Students s ON ga.rfid = s.rfid
            WHERE s.campusid = %s 
            AND DATE(ga.date) = %s 
            AND ga.status = 'Present'
        """

        present_students = {row["rfid"] for row in db.fetch_all(present_students_sql, (campus_id, today))}

        attendance_data = [
            {
                "rfid": student["rfid"],
                "student_name": student["student_name"],
                "status": "Present" if student["rfid"] in present_students else "Absent",
            }
            for student in students
        ]

        present_count = len(present_students)
        absent_count = len(students) - present_count

        return jsonify({
            "success": True,
            "attendance_data": attendance_data,
            "present_count": present_count,
            "absent_count": absent_count,
        }), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@attendance_bp.route('/get_attendance_edit', methods=['GET'])
def get_attendance_edit():
    campus_id = request.args.get('campus_id', type=int)
    year = request.args.get('year', type=int, default=0)
    date_str = request.args.get('date')

    if not campus_id or not date_str:
        return jsonify({"success": False, "error": "Missing required fields"}), 400

    try:
        base_query = "SELECT rfid, student_name FROM Students WHERE campusid = %s"
        params = [campus_id]

        if year > 0:
            base_query += " AND year = %s"
            params.append(year)

        students = db.fetch_all(base_query, tuple(params))

        present_query = """
            SELECT DISTINCT ga.rfid 
            FROM General_Attendance ga
            JOIN Students s ON ga.rfid = s.rfid
            WHERE s.campusid = %s 
            AND DATE(ga.date) = %s 
            AND ga.status = 'Present'
        """
        present_params = [campus_id, date_str]

        if year > 0:
            present_query += " AND s.year = %s"
            present_params.append(year)

        present_students = {row["rfid"] for row in db.fetch_all(present_query, tuple(present_params))}

        attendance_data = [
            {
                "rfid": student["rfid"],
                "student_name": student["student_name"],
                "status": "Present" if student["rfid"] in present_students else "Absent"
            }
            for student in students
        ]

        return jsonify({
            "success": True,
            "attendance_data": attendance_data,
            "present_count": len(present_students),
            "absent_count": len(students) - len(present_students),
        }), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


#Student Dashboard
@attendance_bp.route("/student/attendance_summary", methods=["POST"])
def attendance_summary():
    try:
        data = request.get_json()
        rfid = data.get("rfid")
        if not rfid:
            return jsonify({"error": "rfid is required"}), 400

        # Query subject-level attendance data
        subject_query = """
            SELECT s.subject_name, sa.attendance_status, sa.date, se.TotalDays, se.SubjectAttended
            FROM Subject_Attendance sa
            JOIN Subjects s ON sa.subject_id = s.subject_id
            JOIN Subjects_Enrolled se ON sa.subject_id = se.subject_id AND sa.RFID = se.RFID
            WHERE sa.RFID = %s
        """
        subject_attendance = db.fetch_all(subject_query, (rfid,))

        subject_data = defaultdict(lambda: {
            "name": "",
            "present": 0,
            "absent": 0,
            "total_classes": 0,
            "recent_absences": []
        })

        for row in subject_attendance:
            subject = row["subject_name"]
            status = row["attendance_status"]
            date = row["date"]

            subject_info = subject_data[subject]
            subject_info["name"] = subject
            subject_info["total_classes"] += 1

            if status == "present":
                subject_info["present"] += 1
            elif status == "absent":
                subject_info["absent"] += 1
                if date:
                    subject_info["recent_absences"].append(date.strftime("%Y-%m-%d"))

        for info in subject_data.values():
            total = info["total_classes"] or 1
            info["percentage"] = round((info["present"] / total) * 100)

        # Query general attendance
        general_query = """
            SELECT Status, date
            FROM General_Attendance
            WHERE RFID = %s
        """
        general_attendance = db.fetch_all(general_query, (rfid,))

        total_present = sum(1 for row in general_attendance if row["Status"] == "Present")
        total_absent = sum(1 for row in general_attendance if row["Status"] == "Absent")
        total_classes = len(general_attendance)
        overall_attendance = round((total_present / total_classes) * 100) if total_classes else 0

        # Monthly summary
        monthly_summary = defaultdict(lambda: {"present": 0, "absent": 0})
        for row in general_attendance:
            if not row["date"]:
                continue
            month = row["date"].strftime("%B")
            if row["Status"] == "Present":
                monthly_summary[month]["present"] += 1
            elif row["Status"] == "Absent":
                monthly_summary[month]["absent"] += 1

        print(subject_data)

        return jsonify({
            "status": "success",
            "overall_attendance": overall_attendance,
            "total_present": total_present,
            "total_absent": total_absent,
            "total_classes": total_classes,
            "monthly_summary": [
                {"month": month, **counts}
                for month, counts in monthly_summary.items()
            ],
            "subjects": list(subject_data.values())
        })

    except Exception as e:
        print("Error:", str(e))
        return jsonify({"error": str(e)}), 500