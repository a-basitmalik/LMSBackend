from flask import request, jsonify
from src.DatabaseConnection import Database
from flask import Blueprint

SubjectAttendance_bp = Blueprint('SubjectAttendance', __name__)
db = Database()


# Get all students in a subject
@SubjectAttendance_bp.route('/api/subject/<int:subject_id>/students', methods=['GET'])
def get_subject_students(subject_id):
    query = """
    SELECT s.RFID, s.student_name, s.StudentID
    FROM Students s
    JOIN Subjects_Enrolled se ON s.RFID = se.RFID
    WHERE se.subject_id = %s
    ORDER BY s.student_name
    """
    students = db.fetch_all(query, (subject_id,))

    return jsonify([{
        'rfid': s['RFID'],
        'student_name': s['student_name'],
        'student_id': s['StudentID']
    } for s in students])


# Get attendance for a specific subject and date
@SubjectAttendance_bp.route('/api/subject/<int:subject_id>/attendance', methods=['GET'])
def get_subject_attendance(subject_id):
    date = request.args.get('date')
    if not date:
        return jsonify({'error': 'Date parameter is required'}), 400

    query = """
    SELECT RFID, attendance_status
    FROM Subject_Attendance
    WHERE subject_id = %s AND date = %s
    """
    attendance = db.fetch_all(query, (subject_id, date))

    return jsonify([{
        'rfid': a['RFID'],
        'attendance_status': a['attendance_status']
    } for a in attendance])


# Save attendance for a subject
@SubjectAttendance_bp.route('/api/subject/<int:subject_id>/attendance', methods=['POST'])
def save_subject_attendance(subject_id):
    data = request.get_json()
    if not data or 'date' not in data or 'records' not in data:
        return jsonify({'error': 'Invalid request data'}), 400

    date = data['date']
    records = data['records']

    try:
        # Delete existing attendance records
        delete_query = "DELETE FROM Subject_Attendance WHERE subject_id = %s AND date = %s"
        db.execute_query(delete_query, (subject_id, date))

        # Insert new attendance records
        insert_query = """
        INSERT INTO Subject_Attendance 
        (subject_id, RFID, date, time, attendance_status)
        VALUES (%s, %s, %s, %s, %s)
        """
        for record in records:
            db.execute_query(insert_query, (
                subject_id,
                record['rfid'],
                date,
                record['time'],
                record['attendance_status']
            ))

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
