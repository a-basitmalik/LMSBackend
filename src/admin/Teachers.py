from flask import Blueprint, request, jsonify
from src.DatabaseConnection import Database
from werkzeug.security import generate_password_hash


teacher_bp = Blueprint('teacher', __name__)
db = Database()

@teacher_bp.route('/get_teacher/<teacher_id>', methods=['GET'])
def get_teacher(teacher_id):
    try:
        query = "SELECT * FROM Teacher WHERE id = %s"
        result = db.fetch_one(query, (teacher_id,))

        print("Query Result:", result)  # 🔥 Debugging print

        if not result:
            return jsonify({"message": "Teacher not found"}), 404

        # Convert subjects and feedback from strings to lists
        result["feedback"] = result["feedback"].split(";") if result["feedback"] else []

        return jsonify(result)
    except Exception as e:
        print("Error:", str(e))  # 🔥 Print error in terminal
        return jsonify({"error": str(e)}), 500
        
        

@teacher_bp.route('/get_campuses', methods=['GET'])
def get_campuses():
    try:
        query = "SELECT CampusID, CampusName FROM Campus"
        result = db.fetch_all(query)

        print("Query Result:", repr(result))  # Better debugging output

        if not result:  # Ensure result exists and is not empty
            return jsonify([]), 200  # Return an empty list instead of 404

        campuses = []
        for row in result:
            if "CampusID" in row and "CampusName" in row:  # Ensure keys exist
                campuses.append({
                    "campus_id": row["CampusID"],
                    "campus_name": row["CampusName"]
                })
            else:
                print(f"Skipping invalid row: {repr(row)}")  # Debug missing keys

        return jsonify(campuses), 200
    except Exception as e:
        print("Error in get_campuses:", str(e))
        return jsonify({"error": "Internal Server Error"}), 500


@teacher_bp.route('/get_subjects/<int:campus_id>', methods=['GET'])
def get_subjects(campus_id):
    try:
        query = "SELECT Subject_ID, subject_name FROM Subjects WHERE CampusID = %s"  # Fetch SubjectID too
        result = db.fetch_all(query, (campus_id,))

        if not result:
            return jsonify({"message": "No subjects found for this campus"}), 404

        subjects = [{"subject_id": row["Subject_ID"], "subject_name": row["subject_name"]} for row in result]
        return jsonify(subjects)  # Return a structured list
    except Exception as e:
        print("Error:", str(e))
        return jsonify({"error": str(e)}), 500

@teacher_bp.route('/register_teacher', methods=['POST'])
def register_teacher():
    data = request.json
    teacher_name = data.get('name')
    campus_id = data.get('campus_id')
    password = data.get('password')
    phone = data.get('phone')
    email = f"{teacher_name.lower().replace(' ', '')}@lgscolleges.edu.pk"

    if not teacher_name or not campus_id or not password or not phone:
        return jsonify({'error': 'All fields are required'}), 400


    try:
        query = "SELECT id FROM Teacher WHERE email = %s OR phone = %s"
        existing_teacher = db.fetch_one(query, (email, phone))

        if existing_teacher:
            return jsonify({'error': 'Teacher already exists'}), 400

        insert_query = "INSERT INTO Teacher (name, email, phone, password, campusid) VALUES (%s, %s, %s, %s, %s)"
        db.execute_query(insert_query, (teacher_name, email, phone, password, campus_id))

        return jsonify({'message': 'Teacher registered successfully'}), 201
    except Exception as e:
        print("Error:", str(e))
        return jsonify({'error': str(e)}), 500


