from functools import wraps
import mysql.connector
import logging
from flask import Blueprint, request, jsonify
from src.DatabaseConnection import DB_CONFIG

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

auth_bp = Blueprint('auth', __name__)

class Auth:
    @staticmethod
    def authenticate_user(identifier, password):
        """
        Identifies the user's role based on the provided identifier and password.
        Returns the role and user details if valid, otherwise returns None.
        """
        logging.info(f"Authenticating user with ID: {identifier}")
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        role_queries = {
            'admin': "SELECT username AS id FROM Admin WHERE username = %s AND password = %s",
            'teacher': "SELECT teacherid AS id FROM Teachers WHERE teacherid = %s AND password = %s",
            'student': "SELECT RFID AS id FROM Students WHERE RFID = %s AND password = %s",
            'campus_admin': "SELECT caid AS id FROM CampusAdmin WHERE caid = %s AND password = %s"
        }

        for role, query in role_queries.items():
            logging.info(f"Checking role: {role}")
            cursor.execute(query, (identifier, password))
            user = cursor.fetchone()
            if user:
                logging.info(f"User authenticated as {role} with ID: {user['id']}")
                cursor.close()
                conn.close()
                return role, user['id']  # Return role and user ID

        logging.warning(f"Authentication failed for ID: {identifier}")
        cursor.close()
        conn.close()
        return None, None

@auth_bp.route('/api/login', methods=['POST'])
def login():
    logging.info("Received login request")

    try:
        data = request.get_json()
        logging.info(f"Received request payload: {data}")
    except Exception as e:
        logging.error(f"Failed to parse JSON: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Invalid JSON format'}), 400

    identifier = data.get('id')
    password = data.get('password')

    if not identifier or not password:
        logging.warning("Login failed due to missing ID or password")
        return jsonify({'status': 'error', 'message': 'Missing ID or password'}), 400

    role, user_id = Auth.authenticate_user(identifier, password)

    if role:
        response = {
            'status': 'success',
            'message': 'Login successful',
            'role': role,
            'id': user_id
        }
        logging.info(f"Login successful. Sending response: {response}")
        return jsonify(response), 200, {'Content-Type': 'application/json'}

    logging.warning(f"Invalid login attempt for ID: {identifier}")
    response = {'status': 'error', 'message': 'Invalid credentials'}
    logging.info(f"Sending response: {response}")
    return jsonify(response), 401

@auth_bp.route('/api/logout', methods=['POST'])
def logout():
    logging.info("User logged out successfully")
    response = {'status': 'success', 'message': 'Logged out successfully'}
    logging.info(f"Sending response: {response}")
    return jsonify(response), 200
