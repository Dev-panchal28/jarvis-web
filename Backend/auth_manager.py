# ============================================
# File: auth_manager.py
# Description: PostgreSQL User Auth Manager with Email OTP Reset and Admin Login
# ============================================

import os
import sys
import uuid
import random
import bcrypt
import psycopg2
from datetime import datetime, timedelta
from dotenv import dotenv_values

# === Local Helpers ===
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from jarvis_db import get_user_by_name
from Backend.email_sender import send_otp_email

# === Load .env Variables ===
env_vars = dotenv_values(".env")
DB_PARAMS = {
    "dbname": env_vars.get("PG_DB"),
    "user": env_vars.get("PG_USER"),
    "password": env_vars.get("PG_PASS"),
    "host": env_vars.get("PG_HOST"),
    "port": env_vars.get("PG_PORT", "5432")
}

ADMIN_USERNAME = env_vars.get("ADMIN_USERNAME")
ADMIN_PASSWORD = env_vars.get("ADMIN_PASSWORD")
ADMIN_EMAIL = env_vars.get("ADMIN_EMAIL")

# ============================================
# DB Utilities
# ============================================

def connect_db():
    return psycopg2.connect(**DB_PARAMS)

# ============================================
# Password Hashing
# ============================================

def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

# ============================================
# User Management
# ============================================

def user_exists(username):
    return get_user_by_name(username) is not None

def save_user(email, username, password):
    try:
        with connect_db() as conn:
            with conn.cursor() as cursor:
                user_id = str(uuid.uuid4())
                hashed_pw = hash_password(password)
                cursor.execute("""
                    INSERT INTO users (id, email, username, password, created_at)
                    VALUES (%s, %s, %s, %s, %s)
                """, (user_id, email, username, hashed_pw, datetime.now()))
                cursor.execute("""
                    INSERT INTO sessions (user_id, username, logged_in, last_login)
                    VALUES (%s, %s, 1, %s)
                """, (user_id, username, datetime.now()))
                return True
    except Exception as e:
        print(f"❌ Error saving user: {e}")
        return False

def fetch_user(username):
    with connect_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, password FROM users WHERE username = %s", (username,))
            return cursor.fetchone()

def set_active_user(user_id, username):
    with connect_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO sessions (user_id, username, logged_in, last_login)
                VALUES (%s, %s, 1, %s)
                ON CONFLICT (username) DO UPDATE SET logged_in = 1, last_login = EXCLUDED.last_login
            """, (user_id, username, datetime.now()))

def clear_active_user(username):
    with connect_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE sessions SET logged_in = 0 WHERE username = %s", (username,))

def get_active_user():
    with connect_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT username FROM sessions WHERE logged_in = 1 ORDER BY last_login DESC LIMIT 1")
            result = cursor.fetchone()
            return result[0] if result else None

def email_exists(email):
    with connect_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1 FROM users WHERE email = %s", (email,))
            return cursor.fetchone() is not None

# ============================================
# OTP for Password Reset
# ============================================

def generate_otp():
    return str(random.randint(100000, 999999))

def store_otp(username, otp):
    with connect_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO otp_reset (username, otp, created_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (username) DO UPDATE SET otp = EXCLUDED.otp, created_at = EXCLUDED.created_at
            """, (username, otp, datetime.now()))

def verify_otp(username, otp):
    with connect_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT created_at FROM otp_reset WHERE username = %s AND otp = %s
            """, (username, otp))
            result = cursor.fetchone()
            if result:
                created_at = result[0]
                return datetime.now() - created_at < timedelta(minutes=5)
            return False

def verify_otp_flow(username, otp):
    return verify_otp(username, otp)

def update_password(username, new_password):
    with connect_db() as conn:
        with conn.cursor() as cursor:
            hashed_pw = hash_password(new_password)
            cursor.execute("UPDATE users SET password = %s WHERE username = %s", (hashed_pw, username))

# ============================================
# Signup / Login / Logout
# ============================================

def signup_flow(email, username, password):
    if user_exists(username):
        return False, "⚠️ Username already exists."

    if email_exists(email):
        return False, "⚠️ Email is already registered."

    success = save_user(email, username, password)
    if success:
        return True, "✅ Signup successful. You are now logged in."
    return False, "❌ Signup failed due to a server error."

def is_admin_login(identifier, password):
    return identifier == ADMIN_USERNAME and password == ADMIN_PASSWORD

def login_flow(identifier, password):
    # Check if admin
    if is_admin_login(identifier, password):
        return True, "admin"

    # Else, check user DB
    with connect_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, username, password FROM users WHERE username = %s", (identifier,))
            user = cursor.fetchone()

            if not user:
                cursor.execute("SELECT id, username, password FROM users WHERE email = %s", (identifier,))
                user = cursor.fetchone()
                if not user:
                    return False, "❌ Username or email not found."

            user_id, username, stored_password = user

            if verify_password(password, stored_password):
                set_active_user(user_id, username)
                return True, username

            return False, "❌ Incorrect password."

def logout_flow(username):
    clear_active_user(username)
    print(f"👋 Logged out user: {username}")
    return True

# ============================================
# Forgot / Reset Password Flows
# ============================================

def forgot_password_flow(username):
    user = get_user_by_name(username)
    if not user:
        print("❌ Username does not exist.")
        return False

    email = user.get("email")
    if not email:
        print("❌ No email found for this user.")
        return False

    otp = generate_otp()
    store_otp(username, otp)
    email_sent = send_otp_email(email, otp)

    if email_sent:
        print(f"📩 OTP sent to {email}")
        return True
    else:
        print("❌ Failed to send OTP email.")
        return False

def reset_password_flow(username, otp, new_password):
    if verify_otp(username, otp):
        update_password(username, new_password)
        print("✅ Password updated successfully.")
        return True
    print("❌ Invalid or expired OTP.")
    return False
