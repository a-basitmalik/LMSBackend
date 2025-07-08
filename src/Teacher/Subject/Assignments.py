from flask import Blueprint, jsonify, request
from datetime import datetime
from src.DatabaseConnection import Database

SubjectAssignment_bp = Blueprint('SubjectAssignment', __name__)
db = Database()


@SubjectAssignment_bp.route('/api/subjects/<int:subject_id>/assignments', methods=['GET'])
def get_subject_assignments(subject_id):
    query = """
        SELECT 
            a.assignment_id AS id,
            a.title,
            a.description,
            a.due_date,
            a.posted_date,
            a.status,
            a.total_points,
            (
                SELECT COUNT(*) 
                FROM Submissions s 
                WHERE s.assignment_id = a.assignment_id
            ) AS submitted,
            (
                SELECT COUNT(*) 
                FROM Subjects_Enrolled se 
                WHERE se.subject_id = a.subject_id
            ) AS total
        FROM Assignments a
        WHERE a.subject_id = %s
        ORDER BY a.due_date ASC
    """
    assignments = db.fetch_all(query, (subject_id,))

    # Get attachments for all assignments
    attachment_query = """
        SELECT assignment_id, file_name, file_path
        FROM Assignment_Attachments
        WHERE assignment_id IN (%s)
    """ % ','.join(str(a['id']) for a in assignments) if assignments else "SELECT NULL WHERE FALSE"

    attachments_raw = db.fetch_all(attachment_query)
    attachment_map = {}
    for att in attachments_raw:
        attachment_map.setdefault(att['assignment_id'], []).append({
            'file_name': att['file_name'],
            'file_path': att['file_path']
        })

    for a in assignments:
        a['attachments'] = attachment_map.get(a['id'], [])
        a['due_date'] = a['due_date'].isoformat() if a['due_date'] else None
        a['posted_date'] = a['posted_date'].isoformat() if a['posted_date'] else None

    return jsonify(assignments)


@SubjectAssignment_bp.route('/api/assignments/<int:assignment_id>/submissions', methods=['GET'])
def get_assignment_submissions(assignment_id):
    query = """
        SELECT 
            s.submission_id,
            s.student_rfid,
            st.student_name,
            s.submission_date,
            s.file_name,
            s.file_path,
            s.status,
            s.grade,
            s.feedback
        FROM Submissions s
        JOIN Students st ON st.RFID = s.student_rfid
        WHERE s.assignment_id = %s
        ORDER BY s.submission_date DESC
    """
    submissions = db.fetch_all(query, (assignment_id,))
    for sub in submissions:
        sub['submission_date'] = sub['submission_date'].isoformat() if sub['submission_date'] else None
    return jsonify(submissions)


@SubjectAssignment_bp.route('/api/submissions/<int:submission_id>/grade', methods=['POST'])
def grade_submission(submission_id):
    data = request.get_json()
    grade = data.get('grade')
    feedback = data.get('feedback', '')

    if grade is None:
        return jsonify({'error': 'Grade is required'}), 400

    submission_check = db.fetch_one("SELECT * FROM Submissions WHERE submission_id = %s", (submission_id,))
    if not submission_check:
        return jsonify({'error': 'Submission not found'}), 404

    db.execute_query("""
        UPDATE Submissions
        SET grade = %s,
            feedback = %s,
            status = 'graded'
        WHERE submission_id = %s
    """, (grade, feedback, submission_id))

    return jsonify({
        'message': 'Submission graded successfully',
        'submission_id': submission_id
    })
