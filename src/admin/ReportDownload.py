from flask import Blueprint, request, jsonify, send_from_directory
import os
import pandas as pd
import datetime
from src.DatabaseConnection import Database

report_download_bp = Blueprint('report_download', __name__)
db = Database()

# Folder where Excel files will be saved
GENERATED_FOLDER = os.path.join(os.getcwd(), 'generated_reports')

# Ensure the folder exists
if not os.path.exists(GENERATED_FOLDER):
    os.makedirs(GENERATED_FOLDER)

@report_download_bp.route('/generate-report', methods=['POST'])
def generate_report():
    try:
        data = request.get_json()

        campus_id = data['campus_id']
        report_type = data['report_type']            # "Subject-wise" or "Consolidated"
        subject = data.get('subject')                # Optional
        cls = data.get('class')                      # Optional
        report_category = data.get('report_category')# Optional

        # ✅ Replace this with actual DB query later
        df = pd.DataFrame({
            'Name': ['Zainab', 'Ali'],
            'Marks': [95, 88]
        })

        # 📁 Filename formatting
        now_str = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        safe_subject = subject if subject else report_category or 'General'
        safe_class = cls if cls else 'All'
        filename = f"{report_type}_{safe_subject}_{safe_class}_{now_str}.xlsx"
        filepath = os.path.join(GENERATED_FOLDER, filename)

        # 📝 Save Excel File
        df.to_excel(filepath, index=False)

        # 🧾 Save report metadata in database
        db.insert('''
            INSERT INTO generated_reports 
            (campus_id, report_type, subject, class, report_category, file_path, generated_by) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (
            campus_id,
            report_type,
            subject,
            cls,
            report_category,
            filepath,
            'admin_user'  # Replace with actual admin username if available
        ))

        # 🔗 Return download path
        download_url = f"http://172.16.22.179:5050/admin/download-report/{filename}"
        return jsonify({'success': True, 'path': download_url})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@report_download_bp.route('/download-report/<filename>', methods=['GET'])
def download_report(filename):
    try:
        return send_from_directory(GENERATED_FOLDER, filename, as_attachment=True)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 404