from flask import Blueprint, request, jsonify
from src.DatabaseConnection import Database
import traceback

# Initialize database instance
db = Database()

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/rooms/<int:room_id>/messages', methods=['GET'])
def get_messages_by_room_id(room_id):
    try:
        sql = """
            SELECT m.message_id, m.message_text, m.room_id, m.sender_rfid, m.sent_at,
                   u.student_name AS sender_name
            FROM Messages m
            JOIN Students u ON m.sender_rfid = u.rfid
            WHERE m.room_id = %s
            ORDER BY m.sent_at ASC
        """

        result = db.fetch_all(sql, (room_id,))
        messages = [
            {
                "message_id": row["message_id"],
                "message_text": row["message_text"] or "",
                "room_id": row["room_id"],
                "sender_rfid": row["sender_rfid"],
                "sender_name": row["sender_name"] or "Unknown",
                "sent_at": row["sent_at"].isoformat() if row["sent_at"] else None
            } for row in result
        ]
        return jsonify(messages), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@chat_bp.route('/rooms', methods=['POST'])
def get_or_create_chat_room():
    try:
        data = request.get_json()
        subject_id = int(data.get('subject_id'))

        sql_select = "SELECT room_id FROM ChatRooms WHERE subject_id = %s"
        existing = db.fetch_one(sql_select, (subject_id,))
        if existing:
            return jsonify({"room_id": existing["room_id"]}), 200

        sql_insert = "INSERT INTO ChatRooms (subject_id, created_at) VALUES (%s, NOW())"
        db.execute_query(sql_insert, (subject_id,))
        room_id = db.fetch_one("SELECT LAST_INSERT_ID() AS room_id")['room_id']
        return jsonify({"room_id": room_id}), 200
    except Exception as e:
        print("Error creating chat room:", e)
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@chat_bp.route('/messages', methods=['POST'])
def send_message():
    data = request.get_json()
    room_id = data.get('room_id')
    sender_rfid = data.get('sender_rfid')
    message_text = data.get('message_text')

    if not all([room_id, sender_rfid, message_text]):
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        sql = """
            INSERT INTO Messages (room_id, sender_rfid, message_text, sent_at)
            VALUES (%s, %s, %s, NOW())
        """
        db.execute_query(sql, (room_id, sender_rfid, message_text))
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@chat_bp.route('/read-receipts', methods=['POST'])
def mark_messages_as_read():
    data = request.get_json()
    message_ids = data.get('message_ids')
    reader_rfid = data.get('reader_rfid')

    if not message_ids or not reader_rfid:
        return jsonify({'error': 'Missing message_ids or reader_rfid'}), 400

    try:
        for message_id in message_ids:
            # Check if the read receipt already exists
            check_sql = """
                SELECT 1 FROM ReadReceipts
                WHERE message_id = %s AND reader_rfid = %s
            """
            exists = db.fetch_one(check_sql, (message_id, reader_rfid))
            if exists:
                continue  # Skip if already marked as read

            # Insert read receipt
            insert_sql = """
                INSERT INTO ReadReceipts (message_id, reader_rfid, read_at)
                VALUES (%s, %s, NOW())
            """
            db.execute_query(insert_sql, (message_id, reader_rfid))

        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/rooms/<int:room_id>/messages', methods=['DELETE'])
def clear_chat_history(room_id):
    try:
        sql = "DELETE FROM Messages WHERE room_id = %s"
        db.execute_query(sql, (room_id,))
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/unread-count', methods=['GET'])
def get_unread_message_count():
    try:
        rfid = request.args.get('rfid')
        subject_id = request.args.get('subjectId')

        if not rfid or not subject_id:
            return jsonify({'error': 'Missing rfid or subjectId'}), 400

        # Get the room_id for the subject
        sql_room = "SELECT room_id FROM ChatRooms WHERE subject_id = %s"
        room = db.fetch_one(sql_room, (subject_id,))
        if not room:
            return jsonify({'count': 0}), 200  # No room = no messages

        room_id = room['room_id']

        # Count messages in room NOT read by the user and not sent by the user
        sql_unread_count = """
            SELECT COUNT(*) AS count
            FROM Messages m
            WHERE m.room_id = %s
              AND m.sender_rfid != %s
              AND NOT EXISTS (
                SELECT 1
                FROM ReadReceipts rr
                WHERE rr.message_id = m.message_id AND rr.reader_rfid = %s
              )
        """
        result = db.fetch_one(sql_unread_count, (room_id, rfid, rfid))
        return jsonify({'count': result['count']}), 200

    except Exception as e:
        print('🔥 Error fetching unread message count:', e)
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/message-readers', methods=['POST'])
def get_message_readers():
    try:
        data = request.get_json()
        message_ids = data.get('message_ids')

        if not message_ids or not isinstance(message_ids, list):
            return jsonify({'error': 'Invalid or missing message_ids'}), 400

        # Dynamically create placeholders for the IN clause
        placeholders = ','.join(['%s'] * len(message_ids))
        sql = f"""
            SELECT rr.message_id, s.student_name
            FROM ReadReceipts rr
            JOIN Students s ON rr.reader_rfid = s.RFID
            WHERE rr.message_id IN ({placeholders})
        """

        results = db.fetch_all(sql, tuple(message_ids))

        # Organize results
        readers = {}
        for row in results:
            message_id = row['message_id']
            student_name = row['student_name']
            readers.setdefault(message_id, []).append(student_name)
        print(readers)
        return jsonify({'readers': readers}), 200

    except Exception as e:
        print("🔥 Error in get_message_readers:", e)
        return jsonify({'error': str(e)}), 500
