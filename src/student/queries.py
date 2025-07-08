from flask import Blueprint, request, jsonify
from src.DatabaseConnection import Database

queries_bp = Blueprint('queries', __name__)
db = Database()

@queries_bp.route('/get_queries', methods=['GET'])
def get_queries():
    try:
        student_rfid = request.args.get('student_id')  # frontend uses 'student_id'
        if not student_rfid:
            return jsonify({'error': 'Missing student_id'}), 400

        sql = """
            SELECT q.id, q.question, q.answer, q.status, q.created_at, s.subject_name
            FROM queries q
            JOIN Subjects s ON q.subject_id = s.subject_id
            WHERE q.student_rfid = %s
            ORDER BY q.created_at DESC
        """
        result = db.fetch_all(sql, (student_rfid,))
        queries = [{
            "id": row['id'],
            "subject": row['subject_name'],
            "question": row['question'],
            "answer": row['answer'],
            "isResolved": row['status'] == 'answered',
            "timestamp": row['created_at'].isoformat() if row['created_at'] else None,
        } for row in result]

        return jsonify(queries), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@queries_bp.route('/submit_query', methods=['POST'])
def submit_query():
    try:
        data = request.get_json()
        student_rfid = data.get('student_id')  # frontend sends 'student_id'
        subject_id = data.get('subject_id')
        question = data.get('question')

        if not all([student_rfid, subject_id, question]):
            return jsonify({'error': 'Missing required fields'}), 400

        sql = """
            INSERT INTO queries (student_rfid, subject_id, question)
            VALUES (%s, %s, %s)
        """
        db.execute_query(sql, (student_rfid, subject_id, question))

        new_id = db.fetch_one("SELECT LAST_INSERT_ID() AS id")['id']
        return jsonify({'id': new_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@queries_bp.route('/answer_query/<int:query_id>/answer', methods=['POST'])
def answer_query(query_id):
    try:
        data = request.get_json()
        answer = data.get('answer')

        if not answer:
            return jsonify({'error': 'Answer is required'}), 400

        sql = """
            UPDATE queries
            SET answer = %s, status = 'answered', updated_at = NOW()
            WHERE id = %s
        """
        db.execute_query(sql, (answer, query_id))
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
