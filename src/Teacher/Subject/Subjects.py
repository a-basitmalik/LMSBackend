from flask import jsonify, Blueprint
from datetime import datetime
from src.DatabaseConnection import Database

TeacherSubject_bp = Blueprint('TeacherSubject', __name__)  # You can rename if needed
db = Database()


@TeacherSubject_bp.route('/api/subject/<int:subject_id>/stats', methods=['GET'])
def get_subject_stats(subject_id):
    student_count = db.fetch_one("""
        SELECT COUNT(*) AS total
        FROM Subjects_Enrolled
        WHERE subject_id = %s
    """, (subject_id,)).get('total', 0)

    assignment_count = db.fetch_one("""
        SELECT COUNT(*) AS total
        FROM Assignments
        WHERE subject_id = %s AND status = 'active'
    """, (subject_id,)).get('total', 0)

    attendance_data = db.fetch_one("""
        SELECT 
            COUNT(*) AS total,
            SUM(CASE WHEN attendance_status = 'present' THEN 1 ELSE 0 END) AS present
        FROM Subject_Attendance
        WHERE subject_id = %s AND date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
    """, (subject_id,))

    total = attendance_data.get('total', 0)
    present = attendance_data.get('present', 0)
    attendance_rate = round((present / total) * 100, 2) if total > 0 else 0

    return jsonify({
        'student_count': student_count,
        'assignment_count': assignment_count,
        'attendance_rate': attendance_rate
    })


@TeacherSubject_bp.route('/api/subject/<int:subject_id>/announcements', methods=['GET'])
def get_subject_announcements(subject_id):
    query = """
        SELECT a.id, a.title, a.content, a.created_at, t.name as teacher_name
        FROM Announcements a
        JOIN Teacher t ON a.teacher_id = t.id
        WHERE a.subject_id = %s
        ORDER BY a.created_at DESC
        LIMIT 5
    """
    announcements = db.fetch_all(query, (subject_id,))
    return jsonify([{
        'id': a['id'],
        'title': a['title'],
        'content': a['content'],
        'created_at': a['created_at'].isoformat() if a['created_at'] else None,
        'teacher_name': a['teacher_name']
    } for a in announcements])


@TeacherSubject_bp.route('/api/subject/<int:subject_id>/assignments', methods=['GET'])
def get_subject_assignments(subject_id):
    query = """
        SELECT 
            a.assignment_id, 
            a.title, 
            a.due_date,
            (
                SELECT COUNT(*) 
                FROM Submissions s 
                WHERE s.assignment_id = a.assignment_id
            ) AS submitted_count
        FROM Assignments a
        WHERE a.subject_id = %s AND a.status = 'active'
        ORDER BY a.due_date ASC
        LIMIT 5
    """
    assignments = db.fetch_all(query, (subject_id,))
    return jsonify([{
        'assignment_id': a['assignment_id'],
        'title': a['title'],
        'due_date': a['due_date'].isoformat() if a['due_date'] else None,
        'submitted_count': a['submitted_count']
    } for a in assignments])


@TeacherSubject_bp.route('/api/subject/<int:subject_id>/queries', methods=['GET'])
def get_subject_queries(subject_id):
    query = """
        SELECT 
            q.id, 
            q.question, 
            q.status, 
            q.created_at,
            s.student_name
        FROM queries q
        JOIN Students s ON q.student_rfid = s.RFID
        WHERE q.subject_id = %s
        ORDER BY q.status ASC, q.created_at DESC
        LIMIT 5
    """
    queries = db.fetch_all(query, (subject_id,))
    return jsonify([{
        'id': q['id'],
        'question': q['question'],
        'status': q['status'],
        'created_at': q['created_at'].isoformat() if q['created_at'] else None,
        'student_name': q['student_name']
    } for q in queries])


@TeacherSubject_bp.route('/api/subject/<int:subject_id>/attendance', methods=['GET'])
def get_subject_attendance(subject_id):
    query = """
        SELECT 
            DAYNAME(date) AS day,
            COUNT(*) AS total,
            SUM(CASE WHEN attendance_status = 'present' THEN 1 ELSE 0 END) AS present,
            ROUND(SUM(CASE WHEN attendance_status = 'present' THEN 1 ELSE 0 END) / COUNT(*) * 100, 1) AS attendance_rate
        FROM Subject_Attendance
        WHERE subject_id = %s AND date >= DATE_SUB(CURDATE(), INTERVAL 5 DAY)
        GROUP BY date
        ORDER BY date DESC
        LIMIT 5
    """
    attendance = db.fetch_all(query, (subject_id,))
    return jsonify([{
        'day': a['day'],
        'total': a['total'],
        'present': a['present'],
        'attendance_rate': a['attendance_rate']
    } for a in attendance])
