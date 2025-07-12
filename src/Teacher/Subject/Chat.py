from flask import Blueprint, jsonify, request
from datetime import datetime
from src.DatabaseConnection import Database

Chat_bp = Blueprint('Chat', __name__)
db = Database()


def get_avatar(name):
    if not name:
        return "👤"
    first_char = name[0].upper()
    return "👩‍🎓" if first_char in ['A', 'E', 'I', 'O', 'U'] else "👨‍🎓"


# 🔹 Create or get chat room by subject_id
@Chat_bp.route('/api/chat/rooms/<int:subject_id>', methods=['GET'])
def get_chat_room(subject_id):
    room = db.fetch_one("SELECT room_id FROM ChatRooms WHERE subject_id = %s", (subject_id,))
    if not room:
        db.execute_query(
            "INSERT INTO ChatRooms (subject_id, created_at) VALUES (%s, %s)",
            (subject_id, datetime.utcnow())
        )
        room = db.fetch_one("SELECT room_id FROM ChatRooms WHERE subject_id = %s", (subject_id,))
    return jsonify({'room_id': room['room_id']})


# 🔹 Get all messages for a room
@Chat_bp.route('/api/chat/messages', methods=['GET'])
def get_messages():
    room_id = request.args.get('room_id')
    if not room_id:
        return jsonify({'error': 'room_id is required'}), 400

    messages = db.fetch_all(
        """
        SELECT m.message_id, m.message_text, m.sent_at, u.name, u.role
        FROM Messages m
        JOIN users u ON m.sender_rfid = u.rfid
        WHERE m.room_id = %s
        ORDER BY m.sent_at ASC
        """,
        (room_id,)
    )

    result = []
    for msg in messages:
        result.append({
            'message_id': msg['message_id'],
            'text': msg['message_text'],
            'sender_name': msg['name'],
            'sender_role': msg['role'],
            'timestamp': msg['sent_at'].isoformat() if msg['sent_at'] else None,
            'is_teacher': msg['role'] == 'teacher',
            'avatar': get_avatar(msg['name']),
        })

    return jsonify({'messages': result})


# 🔹 Send new message
@Chat_bp.route('/api/chat/messages', methods=['POST'])
def send_message():
    data = request.get_json()
    required_fields = ['text', 'room_id', 'sender_rfid']

    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400

    db.execute_query(
        """
        INSERT INTO Messages (message_text, room_id, sender_rfid, sent_at)
        VALUES (%s, %s, %s, %s)
        """,
        (data['text'], data['room_id'], data['sender_rfid'], datetime.utcnow())
    )

    sender = db.fetch_one("SELECT name, role FROM users WHERE rfid = %s", (data['sender_rfid'],))
    return jsonify({
        'text': data['text'],
        'room_id': data['room_id'],
        'sender_rfid': data['sender_rfid'],
        'sender_name': sender['name'] if sender else 'Unknown',
        'sender_role': sender['role'] if sender else 'student',
        'timestamp': datetime.utcnow().isoformat(),
        'is_teacher': sender['role'] == 'teacher' if sender else False,
        'avatar': get_avatar(sender['name']) if sender else "👤"
    })
