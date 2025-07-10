import pandas as pd
import os
import datetime
from src.DatabaseConnection import Database

db = Database()

def generate_excel_report(campus_id: int, subject_id: int, assessment_type: str):
    connection = db.connect()
    cursor = connection.cursor(dictionary=True)

    # Query to get all students with their marks for the specified assessment
    query = """
        SELECT 
            s.student_name,
            s.RFID,
            am.total_marks AS total_marks,
            am.Marks_Acheived AS obtained_marks,
            ROUND((am.Marks_Acheived / am.total_marks) * 100, 2) AS percentage
        FROM Students s
        JOIN assessments_marks am ON s.RFID = am.rfid
        JOIN Assessments a ON a.assessment_id = am.assessment_id
        WHERE 
            s.campusid = %s
            AND a.subject_id = %s
            AND a.assessment_type = %s
    """

    cursor.execute(query, (campus_id, subject_id, assessment_type))
    results = cursor.fetchall()
    cursor.close()
    connection.close()

    # Convert to DataFrame
    df = pd.DataFrame(results)

    if df.empty:
        return None  # No data found

    # Rename columns for Excel
    df.rename(columns={
        "student_name": "Student Name",
        "RFID": "RFID",
        "total_marks": "Total Marks",
        "obtained_marks": "Obtained Marks",
        "percentage": "Percentage (%)"
    }, inplace=True)

    # Create output folder if not exists
    output_dir = os.path.join(os.getcwd(), "generated_reports")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # File name
    filename = f"Report_{assessment_type}_{subject_id}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    filepath = os.path.join(output_dir, filename)

    # Save Excel
    df.to_excel(filepath, index=False)

    return filepath

generate_excel_report(1,11,'Send Up')