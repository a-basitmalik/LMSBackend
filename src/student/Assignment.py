from flask import Blueprint, request, jsonify
from src.DatabaseConnection import Database
from werkzeug.utils import secure_filename
import os
assignments_bp = Blueprint('assignments', __name__)
db = Database()
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@assignments_bp.route('/get_assignment', methods=['GET'])
def get_assignments():
    try:
        student_rfid = request.args.get('student_rfid')
        if not student_rfid:
            return jsonify({'error': 'Missing student_rfid'}), 400

        # Fetch the subjects the student is enrolled in
        sql_enrolled_subjects = """
            SELECT subject_id 
            FROM Subjects_Enrolled 
            WHERE RFID = %s
        """
        subjects = db.fetch_all(sql_enrolled_subjects, (student_rfid,))
        subject_ids = [subject['subject_id'] for subject in subjects]

        if not subject_ids:
            return jsonify({'message': 'No subjects found for student'}), 404

        # Prepare the placeholders for the SQL query (IN clause)
        subject_ids_placeholder = ', '.join(['%s'] * len(subject_ids))

        # Fetch the assignments for the subjects the student is enrolled in
        sql_assignments = f"""
            SELECT a.assignment_id, a.subject_id, a.title, a.description, a.due_date, a.posted_date, a.status, s.subject_name
            FROM Assignments a
            JOIN Subjects s ON a.subject_id = s.subject_id
            WHERE a.subject_id IN ({subject_ids_placeholder})
            ORDER BY a.due_date ASC
        """

        result = db.fetch_all(sql_assignments, tuple(subject_ids))

        assignments = []
        for row in result:
            # Fetch attachments for each assignment if they exist
            attachments = fetch_attachments(row['assignment_id'])

            assignments.append({
                "assignment_id": row['assignment_id'],
                "subject_id": row['subject_id'],
                "subject_name": row['subject_name'],
                "title": row['title'],
                "description": row['description'],
                "due_date": row['due_date'].isoformat() if row['due_date'] else None,
                "posted_date": row['posted_date'].isoformat() if row['posted_date'] else None,
                "status": row['status'],
                "attachments": attachments  # Could be an empty list if no attachments
            })

        return jsonify(assignments), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

def fetch_attachments(assignment_id):
    try:
        sql_attachments = """
            SELECT attachment_id, file_name, file_path
            FROM Assignment_Attachments
            WHERE assignment_id = %s
        """
        print(f"Fetching attachments for assignment_id: {assignment_id}")  # Log the assignment_id
        result = db.fetch_all(sql_attachments, (assignment_id,))
        print(f"Found attachments: {result}")  # Log the result

        attachments = [{
            "attachment_id": row['attachment_id'],
            "file_name": row['file_name'],
            "file_path": row['file_path']
        } for row in result]

        return attachments
    except Exception as e:
        print(f"Error fetching attachments: {str(e)}")  # Log the error
        return []


@assignments_bp.route('/submit', methods=['POST'])
def submit_assignment():
    try:
        student_rfid = request.form.get('student_rfid')
        assignment_id = request.form.get('assignment_id')
        file_name = request.form.get('file_name')
        file = request.files.get('file')  # file must come from 'file' key in FormData

        if not all([student_rfid, assignment_id, file_name, file]):
            return jsonify({'error': 'Missing required fields'}), 400

        student_rfid = int(student_rfid)
        assignment_id = int(assignment_id)

        # Secure filename and construct path
        filename = secure_filename(file_name)
        file_path = os.path.join('static', 'Assignments', filename)

        # Save the file
        if not os.path.exists('static/Assignments'):
            os.makedirs('static/Assignments')
        file.save(file_path)

        # Insert into database
        sql_insert_submission = """
            INSERT INTO Submissions (assignment_id, student_rfid, file_name, file_path)
            VALUES (%s, %s, %s, %s)
        """
        db.execute_query(sql_insert_submission, (assignment_id, student_rfid, filename, file_path))

        return jsonify({'message': 'Assignment submitted successfully'}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@assignments_bp.route('/<int:assignment_id>/attachments', methods=['GET'])
def get_attachments(assignment_id):
    try:
        # Fetch attachments for the assignment
        sql_attachments = """
            SELECT attachment_id, file_name, file_path
            FROM Assignment_Attachments
            WHERE assignment_id = %s
        """
        result = db.fetch_all(sql_attachments, (assignment_id,))

        attachments = [{
            "attachment_id": row['attachment_id'],
            "file_name": row['file_name'],
            "file_path": row['file_path']
        } for row in result]

        return jsonify(attachments), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
#
# @assignments_bp.route('/<int:assignment_id>/status', methods=['POST'])
# def update_assignment_status(assignment_id):
#     try:
#         data = request.get_json()
#         status = data.get('status')
#
#         if not status:
#             return jsonify({'error': 'Status is required'}), 400
#
#         # Update assignment status
#         sql_update_status = """
#             UPDATE Assignments
#             SET status = %s
#             WHERE assignment_id = %s
#         """
#         db.execute_query(sql_update_status, (status, assignment_id))
#
#         return jsonify({'message': 'Assignment status updated successfully'}), 200
#
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500


@assignments_bp.route('/<int:assignment_id>/status', methods=['PATCH'])
def update_assignment_status(assignment_id):
    try:
        data = request.get_json()
        new_status = data.get('status')

        if new_status not in ['upcoming', 'active', 'submitted', 'graded']:
            return jsonify({'error': 'Invalid status'}), 400

        sql_update = """
            UPDATE Assignments 
            SET status = %s
            WHERE id = %s
        """
        db.execute_query(sql_update, (new_status, assignment_id))

        return jsonify({'message': 'Status updated successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500