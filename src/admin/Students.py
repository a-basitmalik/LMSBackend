from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
import os
import base64
import time
from src.DatabaseConnection import Database
from datetime import datetime
import traceback



student_bp = Blueprint('student', __name__)
db = Database()


@student_bp.route('/add_student', methods=['POST'])
def add_student():
    data = request.json
    print(f"📥 Incoming Data: {data}")

    try:
        # Extract data
        absentee_id = data.get("absentee_id")
        campus_id = data.get("campus_id")
        fee_amount = data.get("fee_amount")
        password = data.get("password")
        phone_number = data.get("phone_number")
        rfid = data.get("rfid")
        student_id = data.get("student_id")
        student_name = data.get("student_name")
        year = data.get("year")
        photo_base64 = data.get("profile_image")

        print(f"📝 Extracted Data: absentee_id={absentee_id}, campus_id={campus_id}, fee_amount={fee_amount}, "
              f"password={password}, phone_number={phone_number}, rfid={rfid}, student_id={student_id}, "
              f"student_name={student_name}, year={year}, photo_base64={photo_base64[:50]}...")  # Truncate photo base64 for readability

        # Validate RFID
        if not rfid:
            print("⚠️ RFID is missing!")
            return jsonify({"success": False, "error": "RFID cannot be null"}), 400

        # 🔽 Save Image if Provided
        picture_url = None
        if photo_base64:
            try:
                print("🔄 Processing the photo base64 data...")
                filename = secure_filename(f"{rfid}_{int(time.time())}.jpg")
                upload_folder = os.path.join(current_app.root_path, 'static', 'ProfilePictures')
                os.makedirs(upload_folder, exist_ok=True)
                file_path = os.path.join(upload_folder, filename)

                # Decode and save the image
                with open(file_path, "wb") as img_file:
                    img_file.write(base64.b64decode(photo_base64))
                picture_url = f"/static/ProfilePictures/{filename}"
                print(f"🖼️ Saved photo to {file_path} with URL: {picture_url}")
            except Exception as img_error:
                print(f"⚠️ Error saving image: {img_error}")
                picture_url = None  # If image fails to save, keep URL as None

        # 🔽 Insert Student into the Database
        print("🔄 Preparing to insert student into the database...")
        sql = """
            INSERT INTO Students (AbsenteeID, CampusID, DaysAttended, FeeAmount, Fine, Password, Phone_Number, RFID, StudentID, Student_Name, Year, picture_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            absentee_id, campus_id, 0, fee_amount, 0,
            password, phone_number, rfid,
            student_id, student_name, year, picture_url
        )
        print(f"SQL Query: {sql}")
        print(f"Values: {values}")

        db.execute_query(sql, values)
        print("✅ Student added successfully with image.")

        return jsonify({"success": True, "message": "Student added with photo."}), 201

    except Exception as e:
        print(f"🔥 Error in add_student: {e}")
        return jsonify({"success": False, "error": str(e)}), 500



@student_bp.route("/details", methods=["GET"])
def get_student_details():
    try:
        rfid = request.args.get("rfid", type=int)
        query = "SELECT student_name, RFID, year, phone_number, picture_url FROM Students WHERE RFID = %s"
        student = db.fetch_one(query, (rfid,))

        if not student:
            return jsonify({"message": "Student not found"}), 404

        # Modify the picture_url if it exists and is relative
        if student.get("picture_url"):
            base_url = "http://193.203.162.232:5050"  # Your server's base URL
            relative_picture_url = student["picture_url"]
            student["picture_url"] = base_url + relative_picture_url
        return jsonify(student)
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@student_bp.route("/subjects", methods=["GET"])
def get_student_subjects():
    try:
        rfid = request.args.get("rfid", type=int)
        query = """SELECT s.subject_name FROM Subjects_Enrolled se 
                   JOIN Subjects s ON se.subject_id = s.subject_id 
                   WHERE se.RFID = %s"""
        subjects = db.fetch_all(query, (rfid,))

        if not subjects:
            return jsonify({"message": "No subjects found"}), 404

        return jsonify([row["subject_name"] for row in subjects])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@student_bp.route("/attendance", methods=["GET"])
def get_student_attendance():
    try:
        rfid = request.args.get("rfid", type=int)
        query = "SELECT TotalDays, DaysAttended FROM Students WHERE RFID = %s"
        attendance = db.fetch_one(query, (rfid,))

        if not attendance:
            return jsonify({"message": "No attendance data available"}), 404

        attendance["AttendancePercentage"] = round(
            (attendance["DaysAttended"] * 100.0 / attendance["TotalDays"]), 2
        ) if attendance["TotalDays"] > 0 else 0

        return jsonify(attendance)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@student_bp.route("/results", methods=["GET"])
def get_student_results():
    try:
        rfid = request.args.get("rfid", type=int)
        if not rfid:
            return jsonify({"error": "student_id is required"}), 400

        results = {}
        total_marks_all = 0
        total_achieved_all = 0

        # 1. Get all subjects student is enrolled in
        subject_query = """SELECT s.subject_id, s.subject_name 
                           FROM Subjects_Enrolled se 
                           JOIN Subjects s ON se.subject_id = s.subject_id 
                           WHERE se.RFID = %s"""
        subjects = db.fetch_all(subject_query, (rfid,))

        if not subjects:
            return jsonify({"message": "No subjects found"}), 404

        for subject in subjects:
            subject_id = subject["subject_id"]
            subject_name = subject["subject_name"]

            # 2. Get assessment marks for this subject
            assessment_query = """
                SELECT am.Marks_Acheived, a.total_marks 
                FROM assessments_marks am
                JOIN Assessments a ON am.assessment_id = a.assessment_id
                WHERE am.rfid = %s AND a.subject_id = %s
            """
            assessments = db.fetch_all(assessment_query, (rfid, subject_id))

            # 3. Get quiz marks for this subject
            quiz_query = """
                SELECT qm.marks_achieved, q.total_marks 
                FROM quiz_marks qm
                JOIN quizzes q ON qm.quiz_id = q.quiz_id
                WHERE qm.rfid = %s AND q.subject_id = %s
            """
            quizzes = db.fetch_all(quiz_query, (rfid, subject_id))

            # 4. Calculate total marks and percentage
            total_achieved = 0
            total_marks = 0

            for a in assessments:
                if a["Marks_Acheived"] is not None and a["total_marks"]:
                    total_achieved += a["Marks_Acheived"]
                    total_marks += a["total_marks"]

            for q in quizzes:
                if q["marks_achieved"] is not None and q["total_marks"]:
                    total_achieved += q["marks_achieved"]
                    total_marks += q["total_marks"]

            percentage = (total_achieved / total_marks) * 100 if total_marks else 0
            results[subject_name] = f"{percentage:.2f}%"

            total_achieved_all += total_achieved
            total_marks_all += total_marks

        overall_percentage = (total_achieved_all / total_marks_all) * 100 if total_marks_all else 0
        results["Overall"] = f"{overall_percentage:.2f}%"

        return jsonify(results)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@student_bp.route("/fines", methods=["GET"])
def get_student_fines():
    try:
        rfid = request.args.get("rfid", type=int)
        query = "SELECT Fine FROM Students WHERE RFID = %s"
        fine = db.fetch_one(query, (rfid,))

        if not fine:
            return jsonify({"message": "No fines due"}), 404

        return jsonify({"Total Outstanding": f"{fine['Fine']}Rs"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500




@student_bp.route("/upload_photo", methods=["POST"])
def upload_student_photo():
    try:
        rfid = request.args.get("rfid")
        if not rfid:
            return jsonify({"success": False, "message": "RFID is required"}), 400

        image_data = request.data
        if not image_data:
            return jsonify({"success": False, "message": "No image data received"}), 400

        upload_folder = current_app.config['UPLOAD_FOLDER']

        # Generate and save filename
        filename = secure_filename(f"{rfid}_{int(time.time())}.jpg")
        picture_path = os.path.join(upload_folder, filename)

        # Save file to disk
        with open(picture_path, "wb") as f:
            f.write(image_data)

        # Save the path relative to the static/ProfilePictures directory
        relative_path = f"/static/ProfilePictures/{filename}"

        # Update student picture_url in database
        update_query = """
            UPDATE Students SET picture_url = %s WHERE RFID = %s
        """
        db.execute_query(update_query, (relative_path, rfid))

        return jsonify({
            "success": True,
            "photo_url": relative_path
        }), 200

    except Exception as e:
        print(f"🔥 Error uploading photo: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
        
        
#Student Dashboard functions


@student_bp.route("/student_dashboard", methods=["POST"])
def student_dashboard():
    try:
        data = request.get_json()
        rfid = data.get("rfid", None)
        if not rfid:
            return jsonify({"error": "rfid is required"}), 400

        student_query = """
            SELECT student_name, year, picture_url, DaysAttended, TotalDays, campusid 
            FROM Students 
            WHERE RFID = %s
        """
        student = db.fetch_one(student_query, (rfid,))
        if not student:
            return jsonify({"error": "Student not found"}), 404

        name = student.get("student_name") or "Unknown"
        year = student.get("year") or 0
        profile_image = student.get("picture_url") or ""
        days_attended = student.get("DaysAttended") or 0
        total_days = student.get("TotalDays") or 1
        campus_id = student.get("campusid")

        attendance_percentage = round((days_attended / total_days) * 100)
        grade = "First Year" if year == 1 else "Second Year" if year == 2 else str(year)
        section = "A"

        average_score = calculate_average_score(rfid)

        day_today = datetime.today().strftime('%A')
        timetable_query = """
            SELECT s.time, s.subject_name 
            FROM Subjects_Enrolled se
            JOIN Subjects s ON se.subject_id = s.subject_id
            WHERE se.RFID = %s AND s.day = %s
        """
        timetable_data = db.fetch_all(timetable_query, (rfid, day_today))

        timetable = [
            {
                "time": (
                    t["time"].strftime("%H:%M") + " - " +
                    (t["time"].replace(minute=(t["time"].minute + 60) % 60)).strftime("%H:%M")
                ) if t.get("time") else "Not Scheduled",
                "subject": t.get("subject_name") or "Unknown",
                "room": "NA"
            } for t in timetable_data
        ]

        announcements_query = """
            SELECT subject, announcement, created_at
            FROM announcements 
            WHERE campus_id = %s
            ORDER BY created_at DESC
            LIMIT 3
        """
        announcements_data = db.fetch_all(announcements_query, (campus_id,))
        announcements = [
            {
                "title": a.get("subject") or "General",
                "message": a.get("announcement") or "No announcement.",
                "date": "Today"
            } for a in announcements_data
        ]

        return jsonify({
            "status": "success",
            "data": {
                "name": name,
                "grade": grade,
                "section": section,
                "profile_image": profile_image,
                "attendance_percentage": attendance_percentage,
                "average_score": round(average_score),
                "timetable": timetable,
                "announcements": announcements,
                "assignments": [
                    {
                        "subject": "None",
                        "title": "None",
                        "due": "None"
                    }
                ]
            }
        })

    except Exception as e:
        print("Error:", str(e))
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
 

def calculate_average_score(rfid):
    try:
        results = {}
        total_marks_all = 0
        total_achieved_all = 0

        subject_query = """SELECT s.subject_id, s.subject_name 
                           FROM Subjects_Enrolled se 
                           JOIN Subjects s ON se.subject_id = s.subject_id 
                           WHERE se.RFID = %s"""
        subjects = db.fetch_all(subject_query, (rfid,))

        for subject in subjects:
            subject_id = subject["subject_id"]
            subject_name = subject["subject_name"]

            assessment_query = """
                SELECT am.Marks_Acheived, a.total_marks 
                FROM assessments_marks am
                JOIN Assessments a ON am.assessment_id = a.assessment_id
                WHERE am.rfid = %s AND a.subject_id = %s
            """
            assessments = db.fetch_all(assessment_query, (rfid, subject_id))

            quiz_query = """
                SELECT qm.marks_achieved, q.total_marks 
                FROM quiz_marks qm
                JOIN quizzes q ON qm.quiz_id = q.quiz_id
                WHERE qm.rfid = %s AND q.subject_id = %s
            """
            quizzes = db.fetch_all(quiz_query, (rfid, subject_id))

            total_achieved = 0
            total_marks = 0

            for a in assessments:
                if a["Marks_Acheived"] is not None and a["total_marks"]:
                    total_achieved += a["Marks_Acheived"]
                    total_marks += a["total_marks"]

            for q in quizzes:
                if q["marks_achieved"] is not None and q["total_marks"]:
                    total_achieved += q["marks_achieved"]
                    total_marks += q["total_marks"]

            percentage = (total_achieved / total_marks) * 100 if total_marks else 0
            results[subject_name] = f"{percentage:.2f}%"

            total_achieved_all += total_achieved
            total_marks_all += total_marks

        overall_percentage = (total_achieved_all / total_marks_all) * 100 if total_marks_all else 0
        return round(overall_percentage)

    except Exception as e:
        print("Error in calculate_average_score:", str(e))
        return 0
