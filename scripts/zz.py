from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import random  # For simulating sensor data updates
import threading
import time

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Simulated sensor and session data
session_data = {
    1: {"imu": {"x": 0.0, "y": 0.0, "z": 0.0}, "emg": {"analog": 0.0}, "progress": 0},
    2: {"imu": {"x": 0.0, "y": 0.0, "z": 0.0}, "emg": {"analog": 0.0}, "progress": 0},
}
active_session = None
stop_thread = False  # Control variable to stop the update thread


def simulate_sensor_updates():
    """Simulate periodic updates to sensor data."""
    global stop_thread
    while not stop_thread:
        if active_session:
            # Update sensor data for the active session
            session_data[active_session]["imu"] = {
                "x": round(random.uniform(-10.0, 10.0), 2),
                "y": round(random.uniform(-10.0, 10.0), 2),
                "z": round(random.uniform(-10.0, 10.0), 2),
            }
            session_data[active_session]["emg"]["analog"] = round(random.uniform(0.0, 100.0), 2)
            session_data[active_session]["progress"] = min(
                session_data[active_session]["progress"] + random.randint(1, 5), 100
            )
        time.sleep(1)  # Update every second


@app.route("/rehab/start", methods=["POST"])
def start_session():
    global active_session
    data = request.json
    session = data.get("session")
    if session not in session_data:
        return jsonify({"message": "Invalid session"}), 400
    active_session = session
    return jsonify({"message": f"Session {session} started."})


@app.route("/rehab/stop", methods=["POST"])
def stop_session():
    global active_session
    if active_session is None:
        return jsonify({"message": "No active session."}), 400
    session = active_session
    active_session = None
    return jsonify({"message": f"Session {session} stopped."})


@app.route("/rehab/calibrate", methods=["POST"])
def calibrate():
    data = request.json
    session = data.get("session")
    if session not in session_data:
        return jsonify({"message": "Invalid session"}), 400
    return jsonify({"message": f"Calibration for session {session} complete."})


@app.route("/rehab/get_data", methods=["GET"])
def get_data():
    session = request.args.get("session", type=int)
    if session not in session_data:
        return jsonify({"error": "Invalid session"}), 400
    return jsonify(session_data[session])


if __name__ == "__main__":
    # Start the sensor update simulation thread
    thread = threading.Thread(target=simulate_sensor_updates, daemon=True)
    thread.start()
    try:
        app.run(debug=True)
    except KeyboardInterrupt:
        stop_thread = True  # Stop the thread when the server is stopped
        thread.join()
