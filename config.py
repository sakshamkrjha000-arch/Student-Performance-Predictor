"""
config.py
Central configuration for the Student Prediction System.
All secret values are read from environment variables (.env file).
"""
import os

from dotenv import load_dotenv

load_dotenv()  # reads the .env file sitting next to app.py


class Config:
    # ---- Flask ----
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")

    # ---- MySQL ----
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "student_prediction_db")

    # ---- Saved ML models ----
    MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "saved_models")

    PERFORMANCE_MODEL = os.path.join(MODEL_DIR, "performance_model.pkl")
    PLACEMENT_MODEL = os.path.join(MODEL_DIR, "placement_model.pkl")

    # ---- App behaviour ----
    MAX_CONTENT_LENGTH = 1 * 1024 * 1024  # reject uploads larger than 1 MB
