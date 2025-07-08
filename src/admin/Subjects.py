from flask import Blueprint, request, jsonify
from src.DatabaseConnection import Database
import traceback
import random
subject_bp = Blueprint('subject', __name__)
db = Database()


@subject_bp.route('/get_subjects', methods=['GET'])
def get_subjects():
    campus_id = request.args.get('campus_id', type=int)
    year = request.args.get('year', type=int)

    if campus_id is None or year is None:
        return jsonify({"success": False, "error": "Missing campus_id or year"}), 400

    try:
        sql = "SELECT subject_name FROM Subjects WHERE CampusID = %s AND year = %s"
        values = (campus_id, year)

        result = db.fetch_all(sql, values)
        subjects = [row['subject_name'] for row in result]

        return jsonify({"success": True, "subjects": subjects}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# 📌 API: Fetch All Teachers
@subject_bp.route('/api/teachers', methods=['GET'])
def get_teachers():
    try:
        sql = "SELECT id AS id, name AS name FROM Teacher"
        teachers = db.fetch_all(sql)
        return jsonify(teachers), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 📌 API: Fetch All Campuses
@subject_bp.route('/api/campuses', methods=['GET'])
def get_campuses():
    try:
        sql = "SELECT campusid AS campusId, campusname AS campusName FROM Campus"
        campuses = db.fetch_all(sql)
        return jsonify(campuses), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@subject_bp.route('/api/add_subject', methods=['POST'])
def add_subject():
    try:
        data = request.json

        subject_name = data.get('subject_name')
        day = data.get('day')
        time = data.get('time')
        teacher_id = data.get('teacher_id')
        teacher_name = data.get('teacher_name')
        campus_id = data.get('campus_id')
        year = data.get('year')

        if not all([subject_name, day, time, teacher_id, teacher_name, campus_id, year]):
            return jsonify({'error': 'All fields are required'}), 400

        # Generate subject_id using campusid, year, and a two-digit random number
        random_number = random.randint(10, 99)
        subject_id = f"{campus_id}{year}{random_number}"

        sql = """
        INSERT INTO Subjects (subject_id, subject_name, day, time, teacherid, teacher_name, campusid, year)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (subject_id, subject_name, day, time, teacher_id, teacher_name, campus_id, year)
        db.execute_query(sql, values)

        return jsonify({'message': 'Subject added successfully', 'subject_id': subject_id}), 201

    except Exception as e:
        print(traceback.format_exc())  # Log full error traceback
        return jsonify({'error': str(e)}), 500

@subject_bp.route('/get_subjects_dashboard', methods=['GET'])
def get_subjects_dashboard():
    campus_id = request.args.get('campus_id', type=int)

    if campus_id is None:
        return jsonify({"success": False, "error": "Missing campus_id"}), 400

    try:
        sql = """
            SELECT s.subject_id, s.subject_name, s.teacher_name, 
                   (SELECT COUNT(*) FROM Subjects_Enrolled se WHERE se.subject_id = s.subject_id) AS student_count
            FROM Subjects s
            WHERE s.CampusID = %s
        """
        values = (campus_id,)

        result = db.fetch_all(sql, values)
        subjects = [
            {
                "subject_id": row["subject_id"],
                "subject_name": row["subject_name"],
                "teacher_name": row["teacher_name"] if row["teacher_name"] else "Unknown",
                "student_count": row["student_count"]
            }
            for row in result
        ]

        return jsonify({"success": True, "subjects": subjects}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
        
        
#For Student Dashboard

@subject_bp.route('/api/students/<string:rfid>/subjects', methods=['GET'])
def get_subjects_by_rfid(rfid):
    try:
        sql = """
            SELECT s.subject_id, s.subject_name, s.teacher_name
            FROM Subjects s
            JOIN Subjects_Enrolled se ON s.subject_id = se.subject_id
            WHERE se.RFID = %s
        """
        values = (rfid,)
        result = db.fetch_all(sql, values)

        subjects = [
            {
                "id": row["subject_id"] if row["subject_id"] is not None else "None",
                "name": row["subject_name"] if row["subject_name"] is not None else "None",
                "code": row["subject_id"] if row["subject_id"] is not None else "None",  # using subject_id as code
                "instructor": row["teacher_name"] if row["teacher_name"] is not None else "None",
                "description": "None"
            }
            for row in result
        ]
        print(subjects)

        return jsonify({"success": True, "subjects": subjects}), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

