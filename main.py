from flask import Flask, jsonify, request, render_template
import time
import json
import os
import uuid
import logging
from logging.config import fileConfig
from werkzeug.security import generate_password_hash, check_password_hash
import re

# Load logging configuration from file
fileConfig('logging_config.ini')
logger = logging.getLogger()

app = Flask(__name__)

# Uptime tracking
start_time = time.time()

# File paths
messages_file = 'messages.json'
backup_file = 'messages_backup.json'
users_file = 'users.json'

# List of bad words
bad_words = ["fuck", "shit", "bitch", "idiot"]  # Add more words as needed

# Initialize files
def initialize_file(file_name, default_content):
    if not os.path.exists(file_name):
        with open(file_name, 'w') as f:
            json.dump(default_content, f)

initialize_file(messages_file, [])
initialize_file(backup_file, [])
initialize_file(users_file, {})

def load_data(file_name):
    try:
        with open(file_name, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        logger.error(f"Error loading {file_name}. Attempting to load backup.")
        if os.path.exists(backup_file):
            try:
                with open(backup_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                logger.error("Backup file is also missing or corrupted. Reinitializing file.")
        initialize_file(file_name, [])  # Reinitialize file if needed
        return []

def save_data(file_name, data):
    with open(file_name, 'w') as f:
        json.dump(data, f)
    if file_name == messages_file:
        with open(backup_file, 'w') as f:
            json.dump(data, f)

def contains_bad_word(message):
    # Convert message to lowercase and split into words
    words = re.findall(r'\b\w+\b', message.lower())
    # Check if any word is in the list of bad words
    return any(word in bad_words for word in words)

@app.before_request
def log_request_info():
    logger.info(f"Request: {request.method} {request.path}")

@app.route('/')
def home():
    return render_template('guestbook.html')

@app.route('/status')
def status():
    uptime = time.time() - start_time
    return jsonify({
        "status": "running",
        "uptime_seconds": uptime,
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
    })

@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    password = request.form['password']
    if len(password) < 6:
        return jsonify({"success": False, "error": "Password must be at least 6 characters long."})
    users = load_data(users_file)
    if username in users:
        return jsonify({"success": False, "error": "Username already taken."})
    user_id = str(uuid.uuid4())
    hashed_password = generate_password_hash(password)
    users[username] = {"user_id": user_id, "password": hashed_password}
    save_data(users_file, users)
    return jsonify({"success": True, "user_id": user_id, "username": username})

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    users = load_data(users_file)
    user = users.get(username)
    if user and check_password_hash(user['password'], password):
        return jsonify({"success": True, "user_id": user['user_id'], "username": username})
    return jsonify({"success": False, "error": "Invalid username or password."})

@app.route('/logout')
def logout():
    # In a real application, you would handle user sessions and logout functionality here
    return jsonify({"success": True})

@app.route('/submit', methods=['POST'])
def submit():
    message = request.form['message']
    user_id = request.form['user_id']
    users = load_data(users_file)
    username = next((user for user, details in users.items() if details['user_id'] == user_id), None)
    if username is None:
        return jsonify({"success": False, "error": "Invalid user ID."})
    if len(message) > 300:  # Changed limit from 100 to 300
        return jsonify({"success": False, "error": "Message exceeds 200 characters limit."})
    if contains_bad_word(message):
        return jsonify({"success": False, "error": "Message contains inappropriate language."})
    new_message = {"id": str(uuid.uuid4()), "name": username, "message": message, "user_id": user_id}
    messages = load_data(messages_file)
    messages.append(new_message)
    save_data(messages_file, messages)
    return jsonify({"success": True})

@app.route('/messages')
def get_messages():
    messages = load_data(messages_file)
    return jsonify(messages)

@app.route('/delete_message', methods=['POST'])
def delete_message():
    message_id = request.form['id']
    user_id = request.form['user_id']
    messages = load_data(messages_file)
    message = next((msg for msg in messages if msg['id'] == message_id), None)
    if message and message['user_id'] == user_id:
        messages = [msg for msg in messages if msg['id'] != message_id]
        save_data(messages_file, messages)
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "You can only delete your own messages."})

@app.errorhandler(Exception)
def handle_exception(e):
    response = {
        "error": str(e),
        "status": "error",
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
    }
    logger.error(f"Exception: {str(e)}")
    return jsonify(response), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
