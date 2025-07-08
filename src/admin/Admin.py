import mysql.connector
from src.DatabaseConnection import DB_CONFIG
from flask import Blueprint, request, render_template,  jsonify
from werkzeug.utils import secure_filename
import os

from flask import current_app
import mysql.connector

admin_bp = Blueprint('admin', __name__)


def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)
