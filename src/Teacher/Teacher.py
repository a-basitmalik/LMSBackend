from flask import Flask, jsonify, Blueprint
from datetime import datetime
from src.DatabaseConnection import Database  # Ensure this imports your DB wrapper


Teacher_bp = Blueprint('Teacher', __name__)
db = Database()


@Teacher_bp.route('/api/teacher/<int:teacher_id>', methods=['GET'])
def get_teacher(teacher_id):
    teacher = db.fetch_one("SELECT * FROM Teacher WHERE id = %s", (teacher_id,))

    if teacher:
        return jsonify({
            'id': teacher.get('id'),
            'name': teacher.get('name', 'NA'),
            'email': teacher.get('email', 'NA'),
            'department': teacher.get('department', 'NA'),  # Add if exists
            'phone': teacher.get('phone', 'NA'),
            'rating': teacher.get('rating', 'NA')
        })
    else:
        return jsonify({'error': 'Teacher not found'}), 404


@Teacher_bp.route('/api/teacher/<int:teacher_id>/schedule/today', methods=['GET'])
def get_todays_schedule(teacher_id):
    today = datetime.now().strftime('%A')

    query = """
    SELECT s.subject_id, s.subject_name, s.year, ss.class_time, ss.class_day, 
           CONCAT('Room ', FLOOR(1 + RAND() * 20)) as room
    FROM Subjects s
    JOIN Subject_Schedule ss ON s.subject_id = ss.subject_id
    WHERE s.teacherid = %s AND ss.class_day = %s
    ORDER BY ss.class_time
    """

    schedule = db.fetch_all(query, (teacher_id, today))
    return jsonify(schedule)


@Teacher_bp.route('/api/teacher/<int:teacher_id>/subjects', methods=['GET'])
def get_teacher_subjects(teacher_id):
    subjects = db.fetch_all("""
    SELECT subject_id, subject_name, year 
    FROM Subjects 
    WHERE teacherid = %s
    """, (teacher_id,))

    return jsonify(subjects)


@Teacher_bp.route('/api/teacher/<int:teacher_id>/stats', methods=['GET'])
def get_teacher_stats(teacher_id):
    student_result = db.fetch_one("""
    SELECT SUM(student_count) AS student_total
    FROM Subjects 
    WHERE teacherid = %s
    """, (teacher_id,))

    class_result = db.fetch_one("""
    SELECT COUNT(*) AS class_total
    FROM Subjects 
    WHERE teacherid = %s
    """, (teacher_id,))

    return jsonify({
        'student_count': student_result.get('student_total', 0),
        'class_count': class_result.get('class_total', 0),
        'task_count': 0  # You can replace this with real data when implemented
    })


@Teacher_bp.route('/api/teacher/<int:teacher_id>/subjects', methods=['GET'])
def get_Teacher_subjects(teacher_id):
    query = """
    SELECT 
        s.subject_id,
        s.subject_name,
        s.subject_code,
        s.year,
        s.student_count,
        GROUP_CONCAT(DISTINCT CONCAT(s.year, '-', s.class_section) SEPARATOR ',') AS classes,
        GROUP_CONCAT(DISTINCT CONCAT(ss.class_day, ' ', TIME_FORMAT(ss.class_time, '%h:%i %p')) SEPARATOR ',') AS schedule,
        CONCAT('Room ', FLOOR(1 + RAND() * 20)) as room
    FROM Subjects s
    LEFT JOIN Subject_Schedule ss ON s.subject_id = ss.subject_id
    WHERE s.teacherid = %s
    GROUP BY s.subject_id
    """

    results = db.fetch_all(query, (teacher_id,))

    subject_list = []
    for subject in results:
        subject_list.append({
            'subject_id': subject.get('subject_id'),
            'subject_name': subject.get('subject_name', 'NA'),
            'subject_code': subject.get('subject_code', 'NA'),
            'year': subject.get('year', 'NA'),
            'student_count': subject.get('student_count', 0),
            'classes': subject.get('classes', 'NA').split(',') if subject.get('classes') else ['NA'],
            'schedule': subject.get('schedule', 'NA').split(',') if subject.get('schedule') else ['NA'],
            'room': subject.get('room', 'NA')
        })

    return jsonify(subject_list)
