from flask import Flask
from flask_cors import CORS

from src.Teacher.Subject.Assignments import SubjectAssignment_bp
from src.Teacher.Subject.Attendance import SubjectAttendance_bp
from src.Teacher.Subject.Chat import Chat_bp
from src.Teacher.Subject.Queries import SubjectQuery_bp
from src.Teacher.Subject.Results import assessments_bp
from src.Teacher.Subject.Subjects import TeacherSubject_bp
from src.Teacher.Teacher import Teacher_bp
# from src.admin.ReportDownload import report_download_bp
from src.admin.Students import student_bp
from src.admin.Subjects import subject_bp
from src.admin.Campus import campus_bp
from src.admin.Teachers import teacher_bp
from src.Shared import shared_bp
from src.admin.Attendance import attendance_bp
from src.admin.Authentication import auth_bp
from src.admin.Result import result_bp
from src.student.Chat import chat_bp
from src.student.queries import queries_bp
from src.admin.Announcement import announcement_bp
from src.student.Assignment import assignments_bp
import os

app = Flask(__name__)
CORS(app)

app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'static/ProfilePictures')

# Register Blueprints

app.register_blueprint(student_bp, url_prefix='/student')
app.register_blueprint(subject_bp, url_prefix='/subject')
app.register_blueprint(campus_bp, url_prefix='/campus')
app.register_blueprint(teacher_bp, url_prefix='/teacher')
app.register_blueprint(shared_bp, url_prefix='/shared')
app.register_blueprint(attendance_bp, url_prefix='/attendance')
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(result_bp, url_prefix='/result')
app.register_blueprint(announcement_bp, url_prefix='/announcement')
app.register_blueprint(chat_bp, url_prefix='/chat')
app.register_blueprint(queries_bp, url_prefix='/queries')
app.register_blueprint(assignments_bp, url_prefix='/assignments')

app.register_blueprint(Teacher_bp,url_prefix='/Teacher')
app.register_blueprint(TeacherSubject_bp,url_prefix='/TeacherSubject')
app.register_blueprint(SubjectAttendance_bp,url_prefix='/SubjectAttendance')
app.register_blueprint(SubjectQuery_bp,url_prefix='/SubjectQuery')
app.register_blueprint(SubjectAssignment_bp,url_prefix='/SubjectAssignment')
app.register_blueprint(Chat_bp,url_prefix='/SubjectChat')
app.register_blueprint(assessments_bp,url_prefix='/SubjectAssessment')
# app.register_blueprint(report_download_bp,url_prefix='/ReportDownload')


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5050, debug=True)
