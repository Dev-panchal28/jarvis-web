from flask import Flask, render_template, request, jsonify, send_from_directory, session, Response, redirect, url_for
from Backend.chatbot import Chat
from Backend.automation import WriteContent, GoogleSearch, YouTubeSearch, OpenSite, run_automation
from Backend.realtimesearchengine import RealtimeSearchEngine
from Backend.model import FirstLayerDMM
from Backend.speak import speak_text
from Backend.auth_manager import (
    signup_flow, login_flow, logout_flow,
    forgot_password_flow, reset_password_flow, verify_otp_flow
)
from jarvis_db import (
    init_db, get_user_by_name, update_session_login, update_session_logout,
    store_chat, get_chat_history, get_file_by_name,
    get_all_users, delete_user
)
from datetime import timedelta
from dotenv import dotenv_values
import os

SECRET_KEY = os.environ.get("FLASK_SECRET")

# === Flask App Setup ===
app = Flask(__name__)
app.secret_key = SECRET_KEY
app.permanent_session_lifetime = timedelta(days=30)
app.static_folder = 'static'

# === Initialize Database ===
try:
    init_db()
except Exception as e:
    print(f"❌ Failed to initialize DB on app start: {e}")

# === Home Page ===
@app.route("/")
def index():
    username = session.get("username")
    chat_history = get_chat_history(username) if username else []
    return render_template("index.html", chat_history=chat_history, username=username)

# === Chat Route ===
@app.route("/ask", methods=["POST"])
def ask():
    if "username" not in session:
        return jsonify({"response": "❌ Please login first."}), 401

    user_input = request.json.get("message", "").strip()
    if not user_input:
        return jsonify({"response": "⚠️ Empty message received."})

    username = session["username"]
    try:
        if user_input.lower().startswith(("write ", "generate ")):
            response = WriteContent(user_input)
        else:
            tasks = FirstLayerDMM(user_input)
            responses = []
            for task in tasks:
                try:
                    if task.startswith("content"):
                        responses.append(WriteContent(task))
                    elif task.startswith("google search"):
                        responses.append(GoogleSearch(task.replace("google search ", "")))
                    elif task.startswith(("youtube search", "play")):
                        responses.append(YouTubeSearch(task.replace("youtube search ", "").replace("play ", "")))
                    elif task.startswith("open"):
                        responses.append(OpenSite(task.replace("open ", "")))
                    elif task.startswith(("realtime", "real info")):
                        responses.append(RealtimeSearchEngine(user_input))
                    elif task.startswith(("system", "close", "reminder")):
                        responses.append(run_automation(task))
                    else:
                        responses.append(Chat(user_input))
                except Exception as task_error:
                    responses.append(f"❌ Error in task '{task}': {task_error}")
            response = "\n\n".join(responses)

        user = get_user_by_name(username)
        if user:
            store_chat(user["id"], username, user_input, response)

        return jsonify({"response": response})
    except Exception as e:
        return jsonify({"response": f"❌ Internal error: {e}"}), 500

# === Speak Route ===
@app.route("/speak", methods=["POST"])
def speak_route():
    if "username" not in session:
        return jsonify({"error": "❌ Please login first."}), 401

    message = request.json.get("text", "").strip()
    if not message:
        return jsonify({"error": "Empty text"}), 400

    try:
        speak_text(message)
        return send_from_directory("Data", "speech.mp3")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === Signup Route ===
@app.route("/signup", methods=["POST"])
def signup():
    data = request.json
    email = data.get("email", "").strip()
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not email or not username or not password:
        return jsonify({"status": "error", "message": "Email, username, and password required."}), 400

    success, message = signup_flow(email, username, password)
    if success:
        session["username"] = username
        update_session_login(username)
        return jsonify({"status": "success", "message": "✅ Signup successful and logged in."})
    return jsonify({"status": "error", "message": message}), 400

# === Login Route ===
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    identifier = data.get("identifier", "").strip()
    password = data.get("password", "").strip()

    if not identifier or not password:
        return jsonify({"status": "error", "message": "📛 Identifier and password are required."}), 400

    success, result = login_flow(identifier, password)
    if success:
        session["username"] = result
        update_session_login(result)
        return jsonify({"status": "success", "message": f"✅ {result} logged in successfully."})
    return jsonify({"status": "error", "message": result}), 401

# === Logout Route ===
@app.route("/logout", methods=["POST"])
def logout():
    username = session.pop("username", None)
    session.pop("admin", None)
    if username:
        logout_flow(username)
        update_session_logout(username)
        return jsonify({"status": "success", "message": "✅ Logged out successfully."})
    return jsonify({"status": "error", "message": "No active session."})

# === Get Active User ===
@app.route("/get_active_user")
def get_active_user():
    return jsonify({"username": session.get("username")})

# === File Download ===
@app.route("/download/<filename>")
def download(filename):
    if "username" not in session:
        return "❌ Please login first.", 401

    username = session["username"]
    user = get_user_by_name(username)
    if not user:
        return "❌ User not found.", 404

    content = get_file_by_name(user["id"], filename)
    if not content:
        return "❌ File not found.", 404

    return Response(
        content,
        mimetype="text/plain",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )

# === Forgot Password ===
@app.route("/forgot_password", methods=["POST"])
def forgot_password():
    username = request.json.get("username", "").strip()
    if not username:
        return jsonify({"status": "error", "message": "Username required."}), 400

    if forgot_password_flow(username):
        return jsonify({"status": "success", "message": "📩 OTP sent to registered email."})
    return jsonify({"status": "error", "message": "❌ Username does not exist."}), 404

# === Verify OTP ===
@app.route("/verify_otp", methods=["POST"])
def verify_otp():
    data = request.get_json()
    username = data.get("username", "").strip()
    otp = data.get("otp", "").strip()

    if not username or not otp:
        return jsonify({"status": "error", "message": "Username and OTP required."}), 400

    if verify_otp_flow(username, otp):
        return jsonify({"status": "success", "message": "✅ OTP verified."})
    return jsonify({"status": "error", "message": "❌ Invalid or expired OTP."}), 400

# === Reset Password ===
@app.route("/reset_password", methods=["POST"])
def reset_password():
    data = request.json
    username = data.get("username", "").strip()
    otp = data.get("otp", "").strip()
    new_password = data.get("new_password", "").strip()

    if not username or not otp or not new_password:
        return jsonify({"status": "error", "message": "All fields are required."}), 400

    if reset_password_flow(username, otp, new_password):
        return jsonify({"status": "success", "message": "✅ Password reset successful."})
    return jsonify({"status": "error", "message": "❌ Invalid or expired OTP."}), 400

# === Admin Login ===
# === Admin Login (Updated to use auth_manager) ===
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        data = request.json
        identifier = data.get("username", "").strip()
        password = data.get("password", "").strip()

        success, result = login_flow(identifier, password)
        if success and result == "admin":
            session["admin"] = True
            return jsonify({"status": "success", "message": "✅ Admin logged in."})
        return jsonify({"status": "error", "message": "❌ Invalid admin credentials."}), 401

    return render_template("admin_login.html")

# === Admin Dashboard ===
@app.route("/admin")
def admin_dashboard():
    if session.get("admin") != True:
        return redirect(url_for("admin_login"))
    users = get_all_users()
    return render_template("admin.html", users=users)

# === Admin Logout ===
@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.pop("admin", None)
    return jsonify({"status": "success", "message": "✅ Admin logged out."})
@app.route("/admin/delete_user", methods=["POST"])
def delete_user_route():
    # Check if the session has admin privileges
    if session.get("admin") != True:
        return jsonify({"status": "error", "message": "❌ Unauthorized"}), 403

    data = request.json
    username = data.get("username", "").strip()

    # Validate the input
    if not username:
        return jsonify({"status": "error", "message": "⚠️ Username required."}), 400

    try:
        # Call your DB delete function
        if delete_user(username):
            return jsonify({
                "status": "success",
                "message": f"✅ User '{username}' deleted successfully."
            })
        else:
            return jsonify({
                "status": "error",
                "message": "❌ Failed to delete user."
            }), 500

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"❌ Error: {str(e)}"
        }), 500


# === Run Flask App ===
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
