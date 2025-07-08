from flask import jsonify, Blueprint, request
from datetime import datetime
from src.DatabaseConnection import Database

SubjectQuery_bp = Blueprint('SubjectQuery', __name__)
db = Database()


def get_avatar(name):
    if not name:
        return "👤"
    first_char = name[0].upper()
    return "👩‍🎓" if first_char in ['A', 'E', 'I', 'O', 'U'] else "👨‍🎓"


@SubjectQuery_bp.route('/api/subjects/<int:subject_id>/queries', methods=['GET'])
def get_subject_queries(subject_id):
    query = """
        SELECT 
            q.id, 
            q.question, 
            q.status, 
            q.answer,
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
        'student_name': q['student_name'],
        'student_avatar': get_avatar(q['student_name']),
        'response': q['answer']
    } for q in queries])


@SubjectQuery_bp.route('/api/queries/<int:query_id>/respond', methods=['POST'])
def respond_to_query(query_id):
    data = request.get_json()
    response_text = data.get('response')

    if not response_text:
        return jsonify({'error': 'Response text is required'}), 400

    query_check = db.fetch_one("SELECT * FROM queries WHERE id = %s", (query_id,))
    if not query_check:
        return jsonify({'error': 'Query not found'}), 404

    db.execute_query("""
        UPDATE queries
        SET answer = %s,
            status = 'answered',
            updated_at = %s
        WHERE id = %s
    """, (response_text, datetime.utcnow(), query_id))

    return jsonify({
        'message': 'Response submitted successfully',
        'query_id': query_id,
        'status': 'answered'
    })
