from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
from datetime import datetime

app = Flask(__name__)
CORS(app, resources={r"/rehab/*": {"origins": ["http://127.0.0.1:5500", "http://localhost:5500"]}})

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Enhanced data structure
class RehabSession:
    def __init__(self):
        self.session_active = False
        self.session_number = 1  # Default to 1
        self.start_date = datetime.now().strftime("%m/%d/%Y")
        self.exercise_type = "Rehabilitation Exercise"
        self.imu_data = {'x': 0.0, 'y': 0.0, 'z': 0.0}
        self.emg_data = {'analog': 0.0}
        self.progress = {
            'percentage': 50,  # Default to 45% to match frontend
            'target': "Rehabilitation Exercise"
        }

# Global session instance
current_session = RehabSession()

@app.route('/rehab/session_status', methods=['POST'])
def manage_session():
    data = request.json
    status = data.get('status', 0)
    
    if status == 1:  # Start session
        current_session.session_active = True
        current_session.session_number += 1
        current_session.start_date = datetime.now().strftime("%m/%d/%Y")
        current_session.progress['percentage'] = 0
        
        logger.info(f"Session started: Session {current_session.session_number}")
        return jsonify({
            "message": "Session started successfully", 
            "session": {
                "number": current_session.session_number,
                "date": current_session.start_date
            }
        }), 200
    
    elif status == 0:  # Stop session
        if current_session.session_active:
            current_session.session_active = False
            logger.info(f"Session stopped: Session {current_session.session_number}")
            return jsonify({"message": "Session stopped successfully"}), 200
        else:
            return jsonify({"message": "No active session to stop"}), 400

@app.route('/rehab/update_sensor_data', methods=['POST'])
def update_sensor_data():
    data = request.json
    
    # Update IMU data
    if 'imu' in data:
        current_session.imu_data['x'] = data['imu'].get('x', current_session.imu_data['x'])
        current_session.imu_data['y'] = data['imu'].get('y', current_session.imu_data['y'])
        current_session.imu_data['z'] = data['imu'].get('z', current_session.imu_data['z'])
    
    # Update EMG data
    if 'emg' in data:
        current_session.emg_data['analog'] = data['emg'].get('analog', current_session.emg_data['analog'])
    
    # Update progress
    if 'progress' in data:
        current_session.progress['percentage'] = data['progress'].get('percentage', current_session.progress['percentage'])
    
    return jsonify({"message": "Sensor data updated successfully"}), 200

@app.route('/rehab/calibrate', methods=['POST'])
def calibrate():
    # Reset sensor data to initial state
    current_session.imu_data = {'x': 0.0, 'y': 0.0, 'z': 0.0}
    current_session.emg_data = {'analog': 0.0}
    
    logger.info("Calibration performed")
    return jsonify({
        "message": "Calibration successful",
        "calibration_status": True
    }), 200

@app.route('/rehab/get_data', methods=['GET'])
def get_data():
    return jsonify({
        "imu": current_session.imu_data,
        "emg": current_session.emg_data,
        "progress": current_session.progress,
        "session": {
            "number": current_session.session_number,
            "date": current_session.start_date
        }
    }), 200

if __name__ == '__main__':
    app.run(port=5000, debug=True)