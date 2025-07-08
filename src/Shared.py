from flask import Blueprint, jsonify, request
from src.DatabaseConnection import Database

shared_bp = Blueprint('shared', __name__)
db = Database()

@shared_bp.route('/get_students', methods=['GET'])
def get_students():
    try:
        campus_id = request.args.get('campusID')  # Get campusID from request
        if not campus_id:
            return jsonify({"error": "Campus ID is required"}), 400

        query = "SELECT student_name, rfid FROM Students WHERE campusid = %s"
        result = db.fetch_all(query, (campus_id,))

        print(f"Query Executed: {query} | Campus ID: {campus_id}")  # ✅ Debugging print
        print(f"Query Result: {result}")  # ✅ Debugging print for fetched data

        if not result:
            return jsonify({"message": "No students found for this campus"}), 404

        students = [{"student_name": row.get("student_name"), "rfid": row.get("rfid")} for row in result]

        return jsonify(students), 200

    except Exception as e:
        print(f"🔥 Error fetching students: {str(e)}")  # 🔥 Improved error logging
        return jsonify({"error": "An error occurred while fetching students"}), 500

@shared_bp.route('/get_teachers', methods=['GET'])
def get_teachers():
    try:
        campus_id = request.args.get('campusID')  # Get campusID from request
        if not campus_id:
            return jsonify({"error": "Campus ID is required"}), 400

        query = "SELECT id, name FROM Teacher WHERE campusid = %s"
        result = db.fetch_all(query, (campus_id,))

        print(f"Query Executed: {query} | Campus ID: {campus_id}")  # ✅ Debugging print
        print(f"Query Result: {result}")  # ✅ Debugging print for fetched data

        if not result:
            return jsonify({"message": "No teachers found for this campus"}), 404

        teachers = [{"teacher_id": row["id"], "name": row["name"]} for row in result]

        return jsonify(teachers), 200

    except Exception as e:
        print(f"🔥 Error fetching teachers: {str(e)}")  # 🔥 Improved error logging
        return jsonify({"error": "An error occurred while fetching teachers"}), 500


