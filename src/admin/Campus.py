from flask import Blueprint, request, jsonify
from src.DatabaseConnection import Database

campus_bp = Blueprint('campus', __name__)
db = Database()

@campus_bp.route('/get_campuses', methods=['GET'])
def get_campuses():
    try:
        query = "SELECT CampusID, CampusName FROM Campus"  # ✅ Fetch CampusID as well
        result = db.fetch_all(query)

        print("Query Result:", result)  # 🔥 Debugging print

        if not result:
            return jsonify({"message": "No campuses found"}), 404  # Return meaningful response

        # ✅ Include both CampusID and CampusName in JSON response
        campuses = [{"CampusID": row["CampusID"], "CampusName": row["CampusName"]} for row in result]

        return jsonify(campuses)
    except Exception as e:
        print("Error:", str(e))  # 🔥 Print error in terminal
        return jsonify({"error": str(e)}), 500
