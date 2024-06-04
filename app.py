from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash, send_file
from threading import Thread, Event
import soundcard as sc
import soundfile as sf
import sqlite3
import os
from werkzeug.utils import secure_filename
import logging
import datetime

app = Flask(__name__)
app.secret_key = 'workwave office'
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'zip', 'txt', 'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
logging.basicConfig(level=logging.DEBUG)

SAMPLE_RATE = 48000  

recording_event = Event()
recording_thread = None
output_file_name = None

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'zip', 'txt', 'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def record_audio(output_file_name):
    with sc.get_microphone(id=str(sc.default_speaker().name), include_loopback=True).recorder(samplerate=SAMPLE_RATE) as mic:
        with sf.SoundFile(output_file_name, mode='w', samplerate=SAMPLE_RATE, channels=1) as file:
            while recording_event.is_set():
                data = mic.record(numframes=SAMPLE_RATE)
                file.write(data[:, 0])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_db():
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            first_name TEXT NOT NULL,
                            last_name TEXT NOT NULL,
                            email TEXT NOT NULL UNIQUE,
                            password TEXT NOT NULL)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS messages (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            sender_id INTEGER NOT NULL,
                            receiver_id INTEGER NOT NULL,
                            message TEXT NOT NULL,
                            is_file BOOLEAN NOT NULL DEFAULT 0,
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (sender_id) REFERENCES users(id),
                            FOREIGN KEY (receiver_id) REFERENCES users(id))''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS files (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            filename TEXT NOT NULL,
                            filepath TEXT NOT NULL)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS notes (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER NOT NULL,
                            room_name TEXT NOT NULL,
                            content TEXT NOT NULL,
                            color TEXT NOT NULL,
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (user_id) REFERENCES users(id))''')
        conn.commit()

init_db()

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/signup', methods=['POST'])
def signup():
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    email = request.form.get('email')
    password = request.form.get('password')

    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (first_name, last_name, email, password) VALUES (?, ?, ?, ?)", 
                           (first_name, last_name, email, password))
            conn.commit()
            flash('Signed up successfully!', 'success')
        except sqlite3.IntegrityError:
            flash('Email already exists!', 'error')

    return redirect(url_for('home'))

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')

    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, password FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()

        if user and user[1] == password:
            session['user_id'] = user[0]
            session['email'] = email
            flash('Logged in successfully!', 'success')
            return redirect(url_for('chat'))
        else:
            flash('Wrong email or password!', 'error')

    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/chat')
def chat():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    
    user_id = session['user_id']
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT first_name, last_name, email FROM users WHERE id = ?", (user_id,))
        current_user = cursor.fetchone()
        
    if current_user:
        current_user_data = {
            'first_name': current_user[0],
            'last_name': current_user[1],
            'email': current_user[2]
        }
    else:
        current_user_data = {}

    return render_template('chat.html', current_user=current_user_data)

@app.route('/search', methods=['POST'])
def search():
    data = request.get_json()
    search_query = data.get('search_query')
    if not search_query:
        return jsonify([])

    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, first_name, last_name FROM users WHERE first_name LIKE ?", (f'%{search_query}%',))
        results = cursor.fetchall()

    return jsonify(results)

@app.route('/get_messages', methods=['POST'])
def get_messages():
    data = request.get_json()
    chat_user_id = data.get('chat_user_id')
    user_id = session.get('user_id')

    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''SELECT sender_id, message, is_file FROM messages 
                          WHERE (sender_id = ? AND receiver_id = ?)
                          OR (sender_id = ? AND receiver_id = ?)
                          ORDER BY timestamp''', 
                       (user_id, chat_user_id, chat_user_id, user_id))
        messages = cursor.fetchall()

    return jsonify(messages)

@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.get_json()
    receiver_id = data.get('receiver_id')
    message = data.get('message')
    is_file = data.get('is_file', False)
    sender_id = session.get('user_id')

    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO messages (sender_id, receiver_id, message, is_file) VALUES (?, ?, ?, ?)", 
                       (sender_id, receiver_id, message, is_file))
        conn.commit()

    return jsonify(success=True)

@app.route('/get_chat_list')
def get_chat_list():
    current_user_id = session['user_id']

    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''SELECT DISTINCT u.id, u.first_name, u.last_name 
                          FROM users u
                          JOIN messages m 
                          ON u.id = m.sender_id OR u.id = m.receiver_id
                          WHERE (m.sender_id = ? OR m.receiver_id = ?) 
                          AND u.id != ?
                          ORDER BY m.timestamp DESC''', 
                       (current_user_id, current_user_id, current_user_id))
        chat_list = cursor.fetchall()
    return jsonify(chat_list)

@app.route('/update', methods=['POST'])
def update():
    if 'user_id' not in session:
        return redirect(url_for('home'))

    user_id = session['user_id']
    current_password = request.form.get('current_password')
    new_first_name = request.form.get('first_name')
    new_last_name = request.form.get('last_name')
    new_email = request.form.get('email')
    new_password = request.form.get('new_password')

    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM users WHERE id = ?", (user_id,))
        current_user = cursor.fetchone()

        if current_user and current_user[0] == current_password:
            cursor.execute("UPDATE users SET first_name = ?, last_name = ?, email = ?, password = ? WHERE id = ?", 
                           (new_first_name, new_last_name, new_email, new_password, user_id))
            conn.commit()
            flash('Profile updated successfully!', 'success')
        else:
            flash('Incorrect current password!', 'error')

    return redirect(url_for('chat'))

@app.route('/update_profile')
def update_profile():
    if 'user_id' not in session:
        return redirect(url_for('home'))

    user_id = session['user_id']
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT first_name, last_name, email FROM users WHERE id = ?", (user_id,))
        current_user = cursor.fetchone()
        
    if current_user:
        current_user_data = {
            'first_name': current_user[0],
            'last_name': current_user[1],
            'email': current_user[2]
        }
    else:
        current_user_data = {}

    return render_template('update.html', current_user=current_user_data)

@app.route('/upload_file', methods=['POST'])
def upload_file():
    if 'user_id' not in session:
        return redirect(url_for('home'))

    if 'file' not in request.files:
        return jsonify(success=False, error='No file part')

    file = request.files['file']
    if file.filename == '':
        return jsonify(success=False, error='No selected file')

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        with sqlite3.connect('users.db') as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO files (filename, filepath) VALUES (?, ?)", (filename, filepath))
            file_id = cursor.lastrowid
            conn.commit()

        return jsonify(success=True, file_id=file_id)

    return jsonify(success=False, error='File type not allowed')

@app.route('/download/<int:file_id>')
def download_file(file_id):
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT filepath FROM files WHERE id = ?", (file_id,))
        file = cursor.fetchone()
        if file:
            return send_file(file[0], as_attachment=True)
        else:
            return "File not found", 404

@app.route('/lobby')
def lobbyGet():
    return render_template('lobby.html')

@app.route('/room')
def room():
    room_id = request.args.get('room')
    if not room_id:
        return redirect('/lobby')
    return render_template('room.html')

@app.route('/start_recording', methods=['POST'])
def start_recording():
    global recording_thread, output_file_name
    data = request.get_json()
    app.logger.debug(f'Received data: {data}') 
    room_id = data.get('room_id')

    if not room_id:
        return jsonify(status='error', message='Room ID is required'), 400

    if not recording_event.is_set():
        now = datetime.datetime.now()
        dt_string = now.strftime("%d%m%Y_%H%M%S")
        
        folder_path = os.path.join('Audio', room_id)
        os.makedirs(folder_path, exist_ok=True)
        
        output_file_name = os.path.join(folder_path, f"{room_id}_{dt_string}.wav")
        
        recording_event.set()
        recording_thread = Thread(target=record_audio, args=(output_file_name,))
        recording_thread.start()
        
    return jsonify(status='started')

@app.route('/stop_recording', methods=['POST'])
def stop_recording():
    if recording_event.is_set():
        recording_event.clear()
        recording_thread.join()
    return jsonify(status='stopped')

@app.route('/note', methods=['GET', 'POST'])
def note():
    if 'user_id' not in session:
        return redirect(url_for('home'))

    user_id = session['user_id']
    room_name = request.args.get('room_name')

    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT content, color FROM notes WHERE user_id = ? AND room_name = ?", 
                       (user_id, room_name))
        notes = cursor.fetchall()

    return render_template('notes.html', room_name=room_name, notes=notes)

@app.route('/create_note', methods=['POST'])
def create_note():
    if 'user_id' not in session:
        return redirect(url_for('home'))

    user_id = session['user_id']
    room_name = request.form.get('room_name')
    content = request.form.get('content')
    color = request.form.get('color')

    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO notes (user_id, room_name, content, color) VALUES (?, ?, ?, ?)", 
                       (user_id, room_name, content, color))
        conn.commit()
    
    note = {
        'content': content,
        'color': color
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify(success=True, note=note)
    else:
        return redirect(url_for('note', room_name=room_name))

if __name__ == '__main__':
    app.run(debug=True)
