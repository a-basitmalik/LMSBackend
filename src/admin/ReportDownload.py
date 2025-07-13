import tempfile
from flask import Blueprint, request, jsonify, send_file
import os
import pandas as pd 
import traceback
from src.DatabaseConnection import Database

report_download_bp = Blueprint('report_download', __name__)

db = Database()

@report_download_bp.route("/subjects", methods=["GET"])
def get_subjects():
    try:
        campusid = request.args.get('campusid', type=int)
        if not campusid:
            return jsonify({"error": "campusid parameter is required"}), 400

        # Fetch subjects for the given campus
        subjects_query = """
            SELECT subject_id, subject_name, day, 
                   teacher_name, teacherid, year
            FROM Subjects
            WHERE CampusID = %s
            ORDER BY subject_name
        """
        subjects = db.fetch_all(subjects_query, (campusid,))

        if not subjects:
            return jsonify({"message": "No subjects found for this campus"}), 404

        return jsonify(subjects)

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@report_download_bp.route("/subject-report", methods=["POST"])
def subject_report():
    data = request.get_json(force=True)
    campusid  = data["campusid"]
    subjectid = data["subjectid"]
    year      = data["year"]

    # create the report in a temp file
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    tmp.close()
    generate_subject_wise_report(campusid, subjectid, year,
                                 output_file=tmp.name)
    return send_file(tmp.name,
                     as_attachment=True,
                     download_name=f"subject_{subjectid}_report.xlsx")
# --------------------------------------------------------------------
# 1.  /assessment-report      →  generate_assessment_excel
# --------------------------------------------------------------------
@report_download_bp.route("/assessment-report", methods=["POST"])
def assessment_report():
   
    data            = request.get_json(force=True)
    campusid        = data["campusid"]
    subjectid       = data["subjectid"]
    assessment_type = data["assessment_type"]

    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    tmp.close()

    generate_assessment_excel(
        campusid, subjectid, assessment_type, output_file=tmp.name
    )
    return send_file(
        tmp.name,
        as_attachment=True,
        download_name=f"assessment_{subjectid}_{assessment_type}.xlsx",
    )


# --------------------------------------------------------------------
# 2.  /all-subjects-assessments   →  generate_all_subjects_assessments_excel
# --------------------------------------------------------------------
@report_download_bp.route("/all-subjects-assessments", methods=["POST"])
def all_subjects_assessments():
    
    data            = request.get_json(force=True)
    campusid        = data["campusid"]
    year            = data["year"]
    assessment_type = data["assessment_type"]

    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    tmp.close()

    generate_all_subjects_assessments_excel(
        campusid, year, assessment_type, output_file=tmp.name
    )
    return send_file(
        tmp.name,
        as_attachment=True,
        download_name=f"all_subjects_{campusid}_{year}_{assessment_type}.xlsx",
    )


# --------------------------------------------------------------------
# 3.  /all-monthlies-with-quizzes  →  generate_all_monthlies_with_quizzes_excel
# --------------------------------------------------------------------
@report_download_bp.route("/all-monthlies-with-quizzes", methods=["POST"])
def all_monthlies_with_quizzes():
  
    data     = request.get_json(force=True)
    campusid = data["campusid"]
    year     = data["year"]

    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    tmp.close()

    generate_all_monthlies_with_quizzes_excel(
        campusid, year, output_file=tmp.name
    )
    return send_file(
        tmp.name,
        as_attachment=True,
        download_name=f"monthlies_quizzes_{campusid}_{year}.xlsx",
    )



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
        print(" No assessments found for given criteria.")
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

                if percentage >= 95:
                    grade = 'A++'
                elif percentage >= 90:
                    grade = 'A+'
                elif percentage >= 85:
                    grade = 'A'
                elif percentage >= 80:
                    grade = 'B++'
                elif percentage >= 75:
                    grade = 'B+'
                elif percentage >= 70:
                    grade = 'B'
                elif percentage >= 60:
                    grade = 'C'
                elif percentage >= 50:
                    grade = 'D'
                elif percentage >= 40:
                    grade = 'U'
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

    print(f"Excel report generated with multiple {assessment_type} exams: {output_file}")


def generate_all_subjects_assessments_excel(campusid, year, assessment_type, output_file='all_subjects_assessments.xlsx'):
    # Step 1: Fetch all subjects for given campus and year
    subjects_query = """
        SELECT subject_id, subject_name
        FROM Subjects
        WHERE CampusID = %s AND year = %s
    """
    subjects = db.fetch_all(subjects_query, (campusid, year))

    if not subjects:
        print(" No subjects found for the given campus and year.")
        return

    # Step 2: Open ExcelWriter
    with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet('All Assessments')
        writer.sheets['All Assessments'] = worksheet

        current_col = 0  # Start writing from column A
        for subject in subjects:
            subject_id = subject['subject_id']
            subject_name = subject['subject_name']
            current_row = 0  # Reset row to top for each subject block

            # Write subject heading
            worksheet.write(current_row, current_col, f"Subject: {subject_name} (ID: {subject_id})")
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
                worksheet.write(current_row, current_col, f"No {assessment_type} assessments found.")
                current_row += 3
                current_col += 8  # Move to next column block
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
                    if percentage >= 95:
                         grade = 'A++'
                    elif percentage >= 90:
                         grade = 'A+'
                    elif percentage >= 85:
                        grade = 'A'
                    elif percentage >= 80:
                        grade = 'B++'
                    elif percentage >= 75:
                        grade = 'B+'
                    elif percentage >= 70:
                        grade = 'B'
                    elif percentage >= 60:
                        grade = 'C'
                    elif percentage >= 50:
                         grade = 'D'
                    elif percentage >= 40:
                        grade = 'U'
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
                worksheet.write(current_row, current_col, exam_title)
                current_row += 1

                # Write data
                df = pd.DataFrame(data_rows)
                df.to_excel(writer, sheet_name='All Assessments', startrow=current_row, startcol=current_col, index=False, header=True)
                current_row += len(df) + 3  # Padding before next block

            # After finishing this subject, move to the right column block
            current_col += 8  # 6 data columns + 2 spacing
            # current_row is reset at the top of the loop

    print(f" Excel report generated for all subjects in campus {campusid} and year {year}: {output_file}")
 # Padding before next block

def generate_all_monthlies_with_quizzes_excel(campusid, year, output_file='monthly_with_quizzes_all_subjects.xlsx'):
    # Step 1: Get all subjects for this campus and year
    subjects_query = """
        SELECT subject_id, subject_name
        FROM Subjects
        WHERE CampusID = %s AND year = %s
    """
    subjects = db.fetch_all(subjects_query, (campusid, year))
    if not subjects:
        print(" No subjects found.")
        return

    with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
        worksheet = writer.book.add_worksheet("All Monthlies")
        writer.sheets["All Monthlies"] = worksheet

        current_row = 0
        column_offset = 0  # Used to shift columns for each new subject

        for subject in subjects:
            subject_id = subject['subject_id']
            subject_name = subject['subject_name']

            # Step 2: Get all Monthly Assessments for this subject
            monthlies_query = """
                SELECT assessment_id, total_marks, created_at
                FROM Assessments
                WHERE subject_id = %s AND assessment_type = 'Monthly'
                ORDER BY created_at ASC
            """
            monthlies = db.fetch_all(monthlies_query, (subject_id,))
            if not monthlies:
                column_offset += 2  # still move to next block
                continue

            for monthly in monthlies:
                monthly_id = monthly['assessment_id']
                monthly_total = monthly['total_marks']
                monthly_date = monthly['created_at'].strftime("%d-%b-%Y") if monthly['created_at'] else ""

                # Step 3: Get Monthly Marks
                monthly_marks_query = """
                    SELECT S.student_name, S.RFID, AM.Marks_Acheived
                    FROM assessments_marks AM
                    JOIN Students S ON S.RFID = AM.rfid
                    WHERE AM.assessment_id = %s AND S.campusid = %s
                """
                monthly_marks = db.fetch_all(monthly_marks_query, (monthly_id, campusid))
                if not monthly_marks:
                    continue

                # Create student map
                student_map = {row['RFID']: {
                    'Student Name': row['student_name'],
                    'Monthly Marks': row['Marks_Acheived']
                } for row in monthly_marks}

                # Step 4: Get all quizzes for this Monthly
                quizzes_query = """
                    SELECT quiz_id, quiz_number, total_marks
                    FROM quizzes
                    WHERE monthly_assessment_id = %s AND subject_id = %s
                    ORDER BY quiz_number ASC
                """
                quizzes = db.fetch_all(quizzes_query, (monthly_id, subject_id))
                quiz_ids = [q['quiz_id'] for q in quizzes]
                quiz_titles = [f"Quiz {q['quiz_number']}" for q in quizzes]
                quiz_totals = [q['total_marks'] for q in quizzes]

                # Step 5: Get quiz marks
                if quiz_ids:
                    quiz_marks_query = f"""
                        SELECT Q.quiz_id, Q.rfid, Q.marks_achieved
                        FROM quiz_marks Q
                        WHERE Q.quiz_id IN ({','.join(['%s'] * len(quiz_ids))})
                    """
                    quiz_marks = db.fetch_all(quiz_marks_query, (*quiz_ids,))
                    for qmark in quiz_marks:
                        rfid = qmark['rfid']
                        quiz_id = qmark['quiz_id']
                        marks = qmark['marks_achieved']
                        if rfid in student_map:
                            quiz_idx = quiz_ids.index(quiz_id)
                            label = quiz_titles[quiz_idx]
                            student_map[rfid][label] = marks

                # Step 6: Final Calculations
                final_rows = []
                for rfid, data in student_map.items():
                    row = {
                        'Student Name': data['Student Name'],
                        'RFID': rfid
                    }

                    # Add quiz marks
                    quiz_marks_list = []
                    for i, title in enumerate(quiz_titles):
                        mark = data.get(title, 0)
                        quiz_marks_list.append(mark)
                        row[title] = mark

                    monthly_obt = data.get('Monthly Marks', 0)
                    avg_quiz = sum(quiz_marks_list) / len(quiz_marks_list) if quiz_marks_list else 0
                    total_obtained = monthly_obt + avg_quiz
                    total_possible = monthly_total + (quiz_totals[0] if quiz_totals else 0)
                    percentage = (total_obtained / total_possible) * 100 if total_possible > 0 else 0

                    # Grade
                    if percentage >= 95:
                         grade = 'A++'
                    elif percentage >= 90:
                         grade = 'A+'
                    elif percentage >= 85:
                         grade = 'A'
                    elif percentage >= 80:
                         grade = 'B++'
                    elif percentage >= 75:
                          grade = 'B+'
                    elif percentage >= 70:
                         grade = 'B'
                    elif percentage >= 60:
                         grade = 'C'
                    elif percentage >= 50:
                         grade = 'D'
                    elif percentage >= 40:
                         grade = 'U'
                    else:
                         grade = 'F'

                    row['Monthly Marks'] = monthly_obt
                    row['Total Monthly Marks'] = monthly_total
                    row['Total Obtained'] = round(total_obtained, 2)
                    row['Percentage'] = round(percentage, 2)
                    row['Grade'] = grade

                    final_rows.append(row)

                df = pd.DataFrame(final_rows)

                # Step 7: Write to Excel
                heading = f"Subject: {subject_name} | Monthly ID: {monthly_id} | Date: {monthly_date}"
                worksheet.write(current_row, column_offset, heading)
                current_row += 1
                df.to_excel(writer, sheet_name='All Monthlies', startrow=current_row, startcol=column_offset, index=False)
                current_row += len(df) + 3

            # Step 8: Move two columns after one subject is done
            column_offset += df.shape[1] + 2
            current_row = 0  # Reset row so new subject starts from top

    print(f" Excel saved: {output_file}")


def generate_subject_wise_report(campusid, subjectid, year, output_file='subject_report.xlsx'):
    # Step 1: Get subject name
    subject_query = "SELECT subject_name FROM Subjects WHERE subject_id = %s"
    subject_result = db.fetch_one(subject_query, (subjectid,))
    if not subject_result:
        print(" Subject not found.")
        return

    subject_name = subject_result['subject_name']

    # Step 2: Use exact enum values for assessment_type
    assessment_types = [
        'Monthly',
        'Send Up',
        'Mocks',
        'Other',
        'Test Session',
        'Weekly',
        'Half Book',
        'Full Book'
    ]

    with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
        worksheet = writer.book.add_worksheet("Subject Report")
        writer.sheets["Subject Report"] = worksheet

        current_row = 0
        column_offset = 0

        for atype in assessment_types:
            # Step 3: Get all assessments of this type
            assessments_query = """
                SELECT assessment_id, total_marks, created_at
                FROM Assessments
                WHERE subject_id = %s AND assessment_type = %s
                ORDER BY created_at ASC
            """
            assessments = db.fetch_all(assessments_query, (subjectid, atype))

            worksheet.write(current_row, column_offset, f"Subject: {subject_name} | Assessment Type: {atype}")
            current_row += 1

            if not assessments:
                worksheet.write(current_row, column_offset, f"No assessments of type '{atype}' found.")
                current_row += 4
                column_offset += 3
                continue

            for assessment in assessments:
                aid = assessment['assessment_id']
                total = assessment['total_marks']
                date = assessment['created_at'].strftime("%d-%b-%Y") if assessment['created_at'] else ""

                if atype == 'Monthly':
                    # Monthly logic with quizzes
                    monthly_marks_query = """
                        SELECT S.student_name, S.RFID, AM.Marks_Acheived
                        FROM assessments_marks AM
                        JOIN Students S ON S.RFID = AM.rfid
                        WHERE AM.assessment_id = %s AND S.campusid = %s
                    """
                    monthly_marks = db.fetch_all(monthly_marks_query, (aid, campusid))
                    if not monthly_marks:
                        continue

                    student_map = {row['RFID']: {
                        'Student Name': row['student_name'],
                        'Monthly Marks': row['Marks_Acheived']
                    } for row in monthly_marks}

                    quizzes_query = """
                        SELECT quiz_id, quiz_number, total_marks
                        FROM quizzes
                        WHERE monthly_assessment_id = %s AND subject_id = %s
                        ORDER BY quiz_number ASC
                    """
                    quizzes = db.fetch_all(quizzes_query, (aid, subjectid))
                    quiz_ids = [q['quiz_id'] for q in quizzes]
                    quiz_titles = [f"Quiz {q['quiz_number']}" for q in quizzes]
                    quiz_totals = [q['total_marks'] for q in quizzes]

                    if quiz_ids:
                        quiz_marks_query = f"""
                            SELECT quiz_id, rfid, marks_achieved
                            FROM quiz_marks
                            WHERE quiz_id IN ({','.join(['%s'] * len(quiz_ids))})
                        """
                        quiz_marks = db.fetch_all(quiz_marks_query, (*quiz_ids,))
                        for qm in quiz_marks:
                            rfid = qm['rfid']
                            qid = qm['quiz_id']
                            marks = qm['marks_achieved']
                            if rfid in student_map:
                                idx = quiz_ids.index(qid)
                                title = quiz_titles[idx]
                                student_map[rfid][title] = marks

                    final_rows = []
                    for rfid, data in student_map.items():
                        row = {
                            'Student Name': data['Student Name'],
                            'RFID': rfid
                        }

                        quiz_marks_list = []
                        for i, title in enumerate(quiz_titles):
                            mark = data.get(title, 0)
                            quiz_marks_list.append(mark)
                            row[title] = mark

                        monthly_obt = data.get('Monthly Marks', 0)
                        avg_quiz = sum(quiz_marks_list) / len(quiz_marks_list) if quiz_marks_list else 0
                        total_obt = monthly_obt + avg_quiz
                        total_possible = total + (quiz_totals[0] if quiz_totals else 0)
                        percentage = (total_obt / total_possible) * 100 if total_possible > 0 else 0
                        if percentage >= 95:
                            grade = 'A++'
                        elif percentage >= 90:
                            grade = 'A+'
                        elif percentage >= 85:
                            grade = 'A'
                        elif percentage >= 80:
                            grade = 'B++'
                        elif percentage >= 75:
                            grade = 'B+'
                        elif percentage >= 70:
                            grade = 'B'
                        elif percentage >= 60:
                            grade = 'C'
                        elif percentage >= 50:
                            grade = 'D'
                        elif percentage >= 40:
                            grade = 'U'
                        else:
                            grade = 'F'

                        row['Monthly Marks'] = monthly_obt
                        row['Total Monthly Marks'] = total
                        row['Total Obtained'] = round(total_obt, 2)
                        row['Percentage'] = round(percentage, 2)
                        row['Grade'] = grade

                        final_rows.append(row)

                    df = pd.DataFrame(final_rows)
                    worksheet.write(current_row, column_offset, f"Monthly Assessment ID: {aid} | Date: {date}")
                    current_row += 1
                    df.to_excel(writer, sheet_name='Subject Report', startrow=current_row, startcol=column_offset, index=False)
                    current_row += len(df) + 3

                else:
                    # Simple logic for other types
                    marks_query = """
                        SELECT S.student_name, S.RFID, AM.Marks_Acheived
                        FROM assessments_marks AM
                        JOIN Students S ON S.RFID = AM.rfid
                        WHERE AM.assessment_id = %s AND S.campusid = %s
                    """
                    marks = db.fetch_all(marks_query, (aid, campusid))
                    if not marks:
                        continue

                    final_rows = []
                    for m in marks:
                        obt = m['Marks_Acheived']
                        percent = (obt / total) * 100 if total else 0
                        if percent >= 95:
                            grade = 'A++'
                        elif percent >= 90:
                            grade = 'A+'
                        elif percent >= 85:
                            grade = 'A'
                        elif percent >= 80:
                            grade = 'B++'
                        elif percent >= 75:
                            grade = 'B+'
                        elif percent >= 70:
                            grade = 'B'
                        elif percent >= 60:
                            grade = 'C'
                        elif percent >= 50:
                            grade = 'D'
                        elif percent >= 40:
                            grade = 'U'
                        else:
                            grade = 'F'

                        final_rows.append({
                            'Student Name': m['student_name'],
                            'RFID': m['RFID'],
                            'Marks Achieved': obt,
                            'Total Marks': total,
                            'Percentage': round(percent, 2),
                            'Grade': grade
                        })

                    df = pd.DataFrame(final_rows)
                    worksheet.write(current_row, column_offset, f"Assessment ID: {aid} | Date: {date}")
                    current_row += 1
                    df.to_excel(writer, sheet_name='Subject Report', startrow=current_row, startcol=column_offset, index=False)
                    current_row += len(df) + 3

            # Move to next block
            column_offset += df.shape[1] + 3
            current_row = 0

    print(f" Subject report saved: {output_file}")

    # Make sure this is at the bottom of the file:
__all__ = ['report_download_bp']