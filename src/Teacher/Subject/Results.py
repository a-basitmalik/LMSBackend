from flask import Blueprint, request, jsonify, session
from datetime import datetime
import json
from src.DatabaseConnection import Database

assessments_bp = Blueprint('assessments', __name__)
db = Database()


@assessments_bp.route('/api/assessments', methods=['POST'])
def create_assessment():
    data = request.get_json()

    required_fields = ['subject_id', 'assessment_type', 'total_marks', 'grading_criteria', 'created_at']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400

    try:
        subject_id = int(data['subject_id'])
        assessment_type = data['assessment_type']
        total_marks = int(data['total_marks'])
        grading_criteria = data['grading_criteria']
        created_at = datetime.strptime(data['created_at'], '%Y-%m-%dT%H:%M')

        valid_types = ['Monthly', 'Send Up', 'Mocks', 'Other',
                       'Test Session', 'Weekly', 'Half Book', 'Full Book']
        if assessment_type not in valid_types:
            return jsonify({'error': 'Invalid assessment type'}), 400

        # Direct connection for transaction
        conn = db.connect()
        cursor = conn.cursor(dictionary=True)

        # Get teacherid from the subject itself
        cursor.execute("SELECT teacherid FROM Subjects WHERE subject_id = %s", (subject_id,))
        subject_row = cursor.fetchone()

        if not subject_row or not subject_row['teacherid']:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Subject not found or teacher not assigned'}), 404

        teacherid = subject_row['teacherid']

        # Check if an assessment of the same type exists this month
        if assessment_type in ['Monthly', 'Send Up']:
            cursor.execute("""
                SELECT COUNT(*) AS count 
                FROM Assessments 
                WHERE teacherid = %s AND
                      subject_id = %s AND
                      assessment_type = %s AND
                      MONTH(created_at) = %s AND
                      YEAR(created_at) = %s
            """, (teacherid, subject_id, assessment_type, created_at.month, created_at.year))

            result = cursor.fetchone()
            if result['count'] >= 1:
                cursor.close()
                conn.close()
                return jsonify({
                    'error': f'An assessment of type {assessment_type} already exists this month'
                }), 400

        # Determine sequence number
        base_sequence = 0
        if assessment_type == 'Monthly':
            base_sequence = 100
        elif assessment_type == 'Send-Up':
            base_sequence = 150

        cursor.execute("""
            SELECT COALESCE(MAX(sequence), %s - 1) AS max_sequence
            FROM Assessments
            WHERE subject_id = %s AND assessment_type = %s
        """, (base_sequence, subject_id, assessment_type))
        last_sequence = cursor.fetchone()['max_sequence']
        sequence = last_sequence + 1

        # Insert assessment
        cursor.execute("""
            INSERT INTO Assessments 
            (teacherid, subject_id, assessment_type, total_marks, 
             grading_criteria, sequence, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            teacherid,
            subject_id,
            assessment_type,
            total_marks,
            json.dumps(grading_criteria),
            sequence,
            created_at
        ))

        assessment_id = cursor.lastrowid

        # Insert quizzes if Monthly
        if assessment_type == 'Monthly':
            for quiz_number in range(1, 4):
                cursor.execute("""
                    INSERT INTO quizzes 
                    (monthly_assessment_id, quiz_number, created_at, subject_id)
                    VALUES (%s, %s, %s, %s)
                """, (
                    assessment_id,
                    quiz_number,
                    datetime.now(),
                    subject_id
                ))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            'message': 'Assessment created successfully',
            'assessment_id': assessment_id
        }), 201

    except ValueError as e:
        return jsonify({'error': 'Invalid data format', 'details': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'Server error', 'details': str(e)}), 500


@assessments_bp.route('/api/assessments', methods=['GET'])
def get_assessments():
    subject_id = request.args.get('subject_id')
    if not subject_id:
        return jsonify({'error': 'subject_id parameter is required'}), 400

    try:
        # Fetch regular assessments
        raw_assessments = db.fetch_all("""
            SELECT a.assessment_id AS id, a.assessment_type, a.created_at, 
                   a.total_marks, a.sequence, COUNT(am.rfid) > 0 AS is_marked
            FROM Assessments a
            LEFT JOIN assessments_marks am ON a.assessment_id = am.assessment_id
            WHERE a.subject_id = %s
            GROUP BY a.assessment_id
            ORDER BY a.created_at DESC
        """, (subject_id,))

        # Generate titles dynamically
        assessments = []
        for a in raw_assessments:
            title = f"{a['assessment_type']} {a['sequence'] - _get_sequence_base(a['assessment_type'])}"
            a['title'] = title
            assessments.append(a)

        # Fetch quizzes with their parent assessment type + quiz number
        raw_quizzes = db.fetch_all("""
            SELECT q.quiz_id, q.quiz_number, q.created_at, q.total_marks,
                   a.assessment_type, a.sequence,
                   COUNT(qm.rfid) > 0 AS is_marked
            FROM quizzes q
            JOIN Assessments a ON q.monthly_assessment_id = a.assessment_id
            LEFT JOIN quiz_marks qm ON q.quiz_id = qm.quiz_id
            WHERE q.subject_id = %s
            GROUP BY q.quiz_id
            ORDER BY q.created_at DESC
        """, (subject_id,))

        quizzes = []
        for q in raw_quizzes:
            assessment_title = f"{q['assessment_type']} {q['sequence'] - _get_sequence_base(q['assessment_type'])}"
            q['monthly_assessment_title'] = assessment_title
            quizzes.append(q)

        return jsonify({
            'assessments': assessments,
            'quizzes': quizzes
        })

    except Exception as err:
        return jsonify({'error': f'Database error: {str(err)}'}), 500


def _get_sequence_base(assessment_type):
    if assessment_type == 'Monthly':
        return 100
    elif assessment_type == 'Send-Up':
        return 150
    else:
        return 0



@assessments_bp.route('/api/reports/generate', methods=['POST'])
def generate_report():
    data = request.get_json()
    required_fields = ['subject_id', 'assessment_type']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400

    try:
        if data['assessment_type'] == 'Monthly':
            report_data = db.fetch_all("""
                SELECT s.student_name, s.StudentID, am.marks_achieved, a.total_marks
                FROM assessments_marks am
                JOIN Assessments a ON am.assessment_id = a.assessment_id
                JOIN Students s ON am.rfid = s.RFID
                WHERE a.subject_id = %s AND a.assessment_type = 'Monthly'
                ORDER BY s.student_name
            """, (data['subject_id'],))
        else:
            report_data = db.fetch_all("""
                SELECT s.student_name, s.StudentID, am.marks_achieved, a.total_marks
                FROM assessments_marks am
                JOIN Assessments a ON am.assessment_id = a.assessment_id
                JOIN Students s ON am.rfid = s.RFID
                WHERE a.subject_id = %s AND a.assessment_type = %s
                ORDER BY s.student_name
            """, (data['subject_id'], data['assessment_type']))

        # Format report
        formatted_report = []
        for row in report_data:
            percentage = (row['marks_achieved'] / row['total_marks']) * 100
            grade = _calculate_grade(percentage)
            formatted_report.append({
                'student_name': row['student_name'],
                'student_id': row['StudentID'],
                'marks_achieved': row['marks_achieved'],
                'total_marks': row['total_marks'],
                'percentage': round(percentage, 2),
                'grade': grade
            })

        return jsonify({
            'report_type': data['assessment_type'],
            'generated_at': datetime.now().isoformat(),
            'data': formatted_report
        })

    except Exception as err:
        return jsonify({'error': f'Server error: {str(err)}'}), 500


def _calculate_grade(percentage):
    if percentage >= 90: return 'A+'
    elif percentage >= 80: return 'A'
    elif percentage >= 70: return 'B'
    elif percentage >= 60: return 'C'
    elif percentage >= 50: return 'D'
    else: return 'F'



@assessments_bp.route('/api/assessment-marks', methods=['GET'])
def get_assessment_marks():
    assessment_id = request.args.get('assessment_id')
    is_quiz = request.args.get('is_quiz', 'false').lower() == 'true'

    if not assessment_id:
        return jsonify({'error': 'assessment_id parameter is required'}), 400

    try:
        # Get assessment details and compute title
        if is_quiz:
            assessment_details = db.fetch_one("""
                SELECT q.quiz_id, q.quiz_number, q.created_at, q.total_marks,
                       a.assessment_type, a.sequence
                FROM quizzes q
                LEFT JOIN Assessments a ON q.monthly_assessment_id = a.assessment_id
                WHERE q.quiz_id = %s
            """, (assessment_id,))
            if assessment_details:
                assessment_details['monthly_assessment_title'] = (
                    f"{assessment_details['assessment_type']} "
                    f"{assessment_details['sequence'] - _get_sequence_base(assessment_details['assessment_type'])}"
                )
        else:
            assessment_details = db.fetch_one("""
                SELECT assessment_id, assessment_type, created_at, total_marks, sequence
                FROM Assessments
                WHERE assessment_id = %s
            """, (assessment_id,))
            if assessment_details:
                assessment_details['title'] = (
                    f"{assessment_details['assessment_type']} "
                    f"{assessment_details['sequence'] - _get_sequence_base(assessment_details['assessment_type'])}"
                )

        if not assessment_details:
            return jsonify({'error': 'Assessment not found'}), 404

        # Get student marks
        if is_quiz:
            students = db.fetch_all("""
                SELECT s.student_name, s.StudentID, qm.rfid, qm.marks_achieved
                FROM quiz_marks qm
                JOIN Students s ON qm.rfid = s.RFID
                WHERE qm.quiz_id = %s
                ORDER BY s.student_name
            """, (assessment_id,))
        else:
            students = db.fetch_all("""
                SELECT s.student_name, s.StudentID, am.rfid, am.marks_acheived
                FROM assessments_marks am
                JOIN Students s ON am.rfid = s.RFID
                WHERE am.assessment_id = %s
                ORDER BY s.student_name
            """, (assessment_id,))

        return jsonify({
            'assessment_details': assessment_details,
            'students': students
        })

    except Exception as e:
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500



@assessments_bp.route('/api/assessment-students', methods=['GET'])
def get_assessment_students():
    assessment_id = request.args.get('assessment_id')
    is_quiz = request.args.get('is_quiz', 'false').lower() == 'true'

    if not assessment_id:
        return jsonify({'error': 'assessment_id parameter is required'}), 400

    try:
        # Get assessment total marks
        if is_quiz:
            assessment = db.fetch_one("SELECT total_marks FROM quizzes WHERE quiz_id = %s", (assessment_id,))
        else:
            assessment = db.fetch_one("SELECT total_marks FROM Assessments WHERE assessment_id = %s", (assessment_id,))

        if not assessment:
            return jsonify({'error': 'Assessment not found'}), 404

        # Get students with their marks
        if is_quiz:
            query = """
                SELECT s.RFID as rfid, s.student_name, s.StudentID, qm.marks_achieved
                FROM Students s
                JOIN Subjects_Enrolled se ON s.RFID = se.RFID
                JOIN quizzes q ON se.subject_id = q.subject_id
                LEFT JOIN quiz_marks qm ON qm.quiz_id = q.quiz_id AND qm.rfid = s.RFID
                WHERE q.quiz_id = %s
                ORDER BY s.student_name
            """
        else:
            query = """
                SELECT s.RFID as rfid, s.student_name, s.StudentID, am.marks_acheived
                FROM Students s
                JOIN Subjects_Enrolled se ON s.RFID = se.RFID
                JOIN Assessments a ON se.subject_id = a.subject_id
                LEFT JOIN assessments_marks am ON am.assessment_id = a.assessment_id AND am.rfid = s.RFID
                WHERE a.assessment_id = %s
                ORDER BY s.student_name
            """

        students = db.fetch_all(query, (assessment_id,))

        return jsonify({
            'total_marks': assessment['total_marks'],
            'students': students
        })

    except Exception as e:
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500


@assessments_bp.route('/api/submit-marks', methods=['POST'])
def submit_marks():
    data = request.get_json()

    required_fields = ['assessment_id', 'marks', 'is_quiz']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400

    assessment_id = data['assessment_id']
    marks = data['marks']
    is_quiz = data['is_quiz']

    try:
        conn = db.connect()
        cursor = conn.cursor()
        conn.start_transaction()

        for mark in marks:
            rfid = mark['rfid']
            marks_achieved = mark['marks_achieved']

            if is_quiz:
                cursor.execute("""
                    INSERT INTO quiz_marks (quiz_id, rfid, marks_achieved)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE marks_achieved = %s
                """, (assessment_id, rfid, marks_achieved, marks_achieved))
            else:
                cursor.execute("""
                    INSERT INTO assessments_marks (assessment_id, rfid, marks_achieved)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE marks_achieved = %s
                """, (assessment_id, rfid, marks_achieved, marks_achieved))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'message': 'Marks submitted successfully'}), 201

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'error': f'Database error: {str(e)}'}), 500