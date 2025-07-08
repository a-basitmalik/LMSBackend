from flask import Blueprint, request, jsonify
from src.DatabaseConnection import Database

result_bp = Blueprint('result', __name__)
db = Database()


@result_bp.route('/get_students', methods=['GET'])
def get_students():
    try:
        campus_id = request.args.get('campus_id')
        if not campus_id:
            return jsonify({"error": "Missing campus_id parameter"}), 400

        query = "SELECT rfid, student_name, phone_number, year FROM Students WHERE campusid = %s"
        result = db.fetch_all(query, (campus_id,))

        if not result:
            return jsonify({"message": "No students found for the given campus"}), 404

        students = [{
            "student_id": row["rfid"],
            "name": row["student_name"],
            "phone": row["phone_number"],
            "year": row["year"]
        } for row in result]

        return jsonify({"students": students})
    except Exception as e:
        print("Error:", str(e))
        return jsonify({"error": str(e)}), 500

@result_bp.route('/get_assessment_types', methods=['GET'])
def get_assessment_types():
    try:
        query = "SELECT DISTINCT assessment_type FROM Assessments"
        result = db.fetch_all(query)

        # Extract just the values, not dictionaries
        assessment_types = [row['assessment_type'] for row in result]

        return jsonify({"assessment_types": assessment_types})
    except Exception as e:
        print("Error:", str(e))
        return jsonify({"error": str(e)}), 500


@result_bp.route('/get_assessment_monthly', methods=['GET'])
def get_assessment_monthly():
    student_id = request.args.get('student_id')

    if not student_id:
        return jsonify({"error": "Missing student_id"}), 400

    try:
        query = """
            SELECT 
                s.subject_name, 
                q.quiz_number, 
                qm.marks_achieved AS quiz_marks,
                a.total_marks AS assessment_total, 
                am.Marks_Acheived AS assessment_marks,
                DATE_FORMAT(a.created_at, '%M %Y') AS month_year
            FROM Assessments a
            JOIN assessments_marks am ON a.assessment_id = am.assessment_id
            LEFT JOIN quizzes q ON a.assessment_id = q.monthly_assessment_id
            LEFT JOIN quiz_marks qm ON q.quiz_id = qm.quiz_id AND am.rfid = qm.rfid
            JOIN Subjects s ON a.subject_id = s.subject_id
            WHERE a.assessment_type = 'Monthly' AND am.rfid = %s
            ORDER BY a.created_at DESC
        """

        data = db.fetch_all(query, (student_id,))
        print("Raw Query Data:", data)

        # Group data by month and year
        assessments_by_month = {}
        for row in data:
            row["quiz_marks"] = row["quiz_marks"] if row["quiz_marks"] is not None else 0

        for row in data:
            month_year = row.pop("month_year")  # Extract month-year key
            if month_year not in assessments_by_month:
                assessments_by_month[month_year] = []
            assessments_by_month[month_year].append(row)

        print(assessments_by_month)
        return jsonify({"assessments": assessments_by_month})

    except Exception as e:
        print("Error:", str(e))
        return jsonify({"error": str(e)}), 500

@result_bp.route('/get_assessment_else', methods=['GET'])
def get_assessment_else():
    student_id = request.args.get('student_id')
    assessment_type = request.args.get('type')  # Get assessment type from request

    if not student_id or not assessment_type:
        return jsonify({"error": "Missing student_id or type"}), 400

    try:
        query = """
            SELECT 
                s.subject_name, 
                a.total_marks AS assessment_total, 
                am.Marks_Acheived AS assessment_marks,
                a.sequence,
                DATE_FORMAT(a.created_at, '%M %Y') AS month_year
            FROM Assessments a
            JOIN assessments_marks am ON a.assessment_id = am.assessment_id
            JOIN Subjects s ON a.subject_id = s.subject_id
            WHERE a.assessment_type = %s AND am.rfid = %s
            ORDER BY a.created_at DESC
        """

        data = db.fetch_all(query, (assessment_type, student_id))
        print("Raw Query Data:", data)

        # Group data by month and year
        assessments_by_month = {}
        for row in data:
            row["assessment_marks"] = row["assessment_marks"] if row["assessment_marks"] is not None else 0

        for row in data:
            month_year = row.pop("month_year")  # Extract month-year key
            if month_year not in assessments_by_month:
                assessments_by_month[month_year] = []
            assessments_by_month[month_year].append(row)

        print(assessments_by_month)
        return jsonify({"assessments": assessments_by_month})

    except Exception as e:
        print("Error:", str(e))
        return jsonify({"error": str(e)}), 500
