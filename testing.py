import pandas as pd
from src.DatabaseConnection import Database  # Update with actual import path

db = Database()

def generate_assessment_excel(campusid, subject_id, assessment_type, output_file='assessment_report.xlsx'):
    # Step 1: Fetch matching assessments
    assessment_query = """
        SELECT A.assessment_id, A.total_marks, A.created_at
        FROM Assessments A
        WHERE A.subject_id = %s AND A.assessment_type = %s
        ORDER BY A.created_at ASC
    """
    assessments = db.fetch_all(assessment_query, (subject_id, assessment_type))

    if not assessments:
        print("❌ No assessments found for given criteria.")
        return

    # Step 2: Use ExcelWriter to manually control layout
    with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet('Assessments')
        writer.sheets['Assessments'] = worksheet

        current_row = 0
        for idx, assessment in enumerate(assessments, start=1):
            assessment_id = assessment['assessment_id']
            fallback_total_marks = assessment['total_marks']
            created_at = assessment.get('created_at')

            # Fetch student marks for this assessment
            marks_query = """
                SELECT S.student_name, S.RFID, AM.Marks_Acheived, AM.total_marks
                FROM assessments_marks AM
                JOIN Students S ON S.RFID = AM.rfid
                WHERE AM.assessment_id = %s AND S.campusid = %s
            """
            marks_data = db.fetch_all(marks_query, (assessment_id, campusid))

            data_rows = []
            for row in marks_data:
                obtained = row['Marks_Acheived']
                total = row['total_marks'] or fallback_total_marks or 0
                percentage = (obtained / total) * 100 if total > 0 else 0

                # Grade assignment
                if percentage >= 90:
                    grade = 'A+'
                elif percentage >= 80:
                    grade = 'A'
                elif percentage >= 70:
                    grade = 'B'
                elif percentage >= 60:
                    grade = 'C'
                elif percentage >= 50:
                    grade = 'D'
                else:
                    grade = 'F'

                data_rows.append({
                    'Student Name': row['student_name'],
                    'RFID': row['RFID'],
                    'Marks Achieved': obtained,
                    'Total Marks': total,
                    'Percentage': round(percentage, 2),
                    'Grade': grade
                })

            # Write assessment title
            exam_title = f"{assessment_type} Exam {idx}"
            if created_at:
                exam_title += f" ({created_at.strftime('%d-%b-%Y')})"
            worksheet.write(current_row, 0, exam_title)
            current_row += 1

            # Write data
            df = pd.DataFrame(data_rows)
            df.to_excel(writer, sheet_name='Assessments', startrow=current_row, index=False, header=True)

            current_row += len(df) + 3  # Leave 3 empty rows before next exam

    print(f"✅ Excel report generated with multiple {assessment_type} exams: {output_file}")


def generate_all_subjects_assessments_excel(campusid, year, assessment_type, output_file='all_subjects_assessments.xlsx'):
    # Step 1: Fetch all subjects for given campus and year
    subjects_query = """
        SELECT subject_id, subject_name
        FROM Subjects
        WHERE CampusID = %s AND year = %s
    """
    subjects = db.fetch_all(subjects_query, (campusid, year))

    if not subjects:
        print("❌ No subjects found for the given campus and year.")
        return

    # Step 2: Open ExcelWriter
    with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet('All Assessments')
        writer.sheets['All Assessments'] = worksheet

        current_row = 0

        for subject in subjects:
            subject_id = subject['subject_id']
            subject_name = subject['subject_name']

            # Write subject heading
            worksheet.write(current_row, 0, f"Subject: {subject_name} (ID: {subject_id})")
            current_row += 1

            # Step 3: Fetch all assessments for the subject
            assessments_query = """
                SELECT A.assessment_id, A.total_marks, A.created_at
                FROM Assessments A
                WHERE A.subject_id = %s AND A.assessment_type = %s
                ORDER BY A.created_at ASC
            """
            assessments = db.fetch_all(assessments_query, (subject_id, assessment_type))

            if not assessments:
                worksheet.write(current_row, 0, f"No {assessment_type} assessments found.")
                current_row += 3
                continue

            for idx, assessment in enumerate(assessments, start=1):
                assessment_id = assessment['assessment_id']
                fallback_total = assessment['total_marks']
                created_at = assessment['created_at']

                # Step 4: Fetch student marks for the assessment
                marks_query = """
                    SELECT S.student_name, S.RFID, AM.Marks_Acheived, AM.total_marks
                    FROM assessments_marks AM
                    JOIN Students S ON S.RFID = AM.rfid
                    WHERE AM.assessment_id = %s AND S.campusid = %s
                """
                marks_data = db.fetch_all(marks_query, (assessment_id, campusid))

                # Format student data
                data_rows = []
                for row in marks_data:
                    obtained = row['Marks_Acheived']
                    total = row['total_marks'] or fallback_total or 0
                    percentage = (obtained / total) * 100 if total > 0 else 0

                    if percentage >= 90:
                        grade = 'A+'
                    elif percentage >= 80:
                        grade = 'A'
                    elif percentage >= 70:
                        grade = 'B'
                    elif percentage >= 60:
                        grade = 'C'
                    elif percentage >= 50:
                        grade = 'D'
                    else:
                        grade = 'F'

                    data_rows.append({
                        'Student Name': row['student_name'],
                        'RFID': row['RFID'],
                        'Marks Achieved': obtained,
                        'Total Marks': total,
                        'Percentage': round(percentage, 2),
                        'Grade': grade
                    })

                # Step 5: Write assessment heading
                exam_title = f"{assessment_type} Exam {idx}"
                if created_at:
                    exam_title += f" ({created_at.strftime('%d-%b-%Y')})"
                worksheet.write(current_row, 0, exam_title)
                current_row += 1

                # Write data
                df = pd.DataFrame(data_rows)
                df.to_excel(writer, sheet_name='All Assessments', startrow=current_row, index=False, header=True)
                current_row += len(df) + 3  # Padding before next block

    print(f"✅ Excel report generated for all subjects in campus {campusid} and year {year}: {output_file}")


# generate_assessment_excel(campusid=1, subject_id=11, assessment_type='Monthly')
generate_all_subjects_assessments_excel(campusid=1, year=1, assessment_type='Monthly')
