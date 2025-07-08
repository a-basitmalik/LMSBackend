from flask import Blueprint, request, jsonify
from datetime import datetime
from src.DatabaseConnection import Database

announcement_bp = Blueprint('announcement', __name__)
db = Database()

@announcement_bp.route('/create', methods=['POST'])
def create_announcement():
    try:
        # Get the JSON data from the request
        data = request.get_json()

        # Print the received data
        print(f"Received data: {data}")

        subject = data.get('subject')
        announcement = data.get('announcement')
        audience_type = data.get('audience_type')
        subject_groups = data.get('subject_groups', [])
        campus_id = data.get('campus_id')  # New campus_id field

        # Validate input
        if not subject or not announcement or not audience_type or not campus_id:
            print(f"Missing required fields: subject={subject}, announcement={announcement}, audience_type={audience_type}, campus_id={campus_id}")
            return jsonify({"success": False, "message": "All fields are required!"}), 400

        # Initialize the database instance
        db_instance = Database()

        # Optional: Check if an announcement already exists for the same subject
        check_announcement_sql = """
            SELECT COUNT(*) FROM announcements 
            WHERE subject = %s AND audience_type = %s AND campus_id = %s AND created_at >= CURRENT_DATE
        """
        print(f"Executing SQL: {check_announcement_sql}")
        result = db_instance.fetch_one(check_announcement_sql, (subject, audience_type, campus_id))

        if result and result['COUNT(*)'] > 0:
            print(f"An announcement with the same subject already exists today for this campus. Subject: {subject}, Audience Type: {audience_type}, Campus ID: {campus_id}")
            return jsonify({"success": False, "message": "An announcement with the same subject already exists today for this campus."}), 400

        # Insert the new announcement into the database
        insert_announcement_sql = """
            INSERT INTO announcements (subject, announcement, audience_type, subject_groups, campus_id, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        print(f"Executing SQL: {insert_announcement_sql}")
        db_instance.execute_query(insert_announcement_sql, (subject, announcement, audience_type, ','.join(subject_groups), campus_id, datetime.now()))

        # Print success message
        print(f"Announcement created successfully: Subject={subject}, Audience Type={audience_type}, Campus ID={campus_id}")

        return jsonify({"success": True, "message": "Announcement created successfully!"}), 201

    except Exception as e:
        # Print error message
        print(f"Error occurred while creating the announcement: {str(e)}")
        # Handle exceptions and return an error message
        return jsonify({"success": False, "message": str(e)}), 500
