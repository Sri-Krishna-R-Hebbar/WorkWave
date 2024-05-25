from flask import Flask, render_template, jsonify, request, redirect, url_for
import soundcard as sc
import soundfile as sf
from threading import Thread, Event
import datetime
import os
import logging

app = Flask(__name__)
app.logger.setLevel(logging.DEBUG) 

SAMPLE_RATE = 48000  

recording_event = Event()
recording_thread = None
output_file_name = None

def record_audio(output_file_name):
    with sc.get_microphone(id=str(sc.default_speaker().name), include_loopback=True).recorder(samplerate=SAMPLE_RATE) as mic:
        with sf.SoundFile(output_file_name, mode='w', samplerate=SAMPLE_RATE, channels=1) as file:
            while recording_event.is_set():
                data = mic.record(numframes=SAMPLE_RATE)
                file.write(data[:, 0])

@app.route('/')
def index():
    return render_template('room.html')

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

if __name__ == '__main__':
    app.run(debug=True)
